# KRX 데이터 소스 — 분야별 추천 시세 (08-krx-recommend.md)

**상태:** 완료 (Phase 1, 단위 테스트)  
**변경일:** 2024년  
**영향:** `app/config.py`, `app/stocks/krx.py`, `app/routers/recommend.py`, `backend/.env.example`

---

## 개요

분야별 추천 종목의 시세 데이터 소스를 **KIS(기본값) ↔ KRX** 토글로 전환할 수 있게 만들었다.

### 왜?

- **KIS 의존 제거:** 추천 파이프라인이 KIS에만 의존하면, KIS 호출 한계나 장애 시 추천이 불가능해진다.
- **KRX 일별매매:** KRX 데이터 OpenAPI는 장 종료 후 일별매매 스냅샷을 제공한다(948 KOSPI + 1822 KOSDAQ 종목).
- **실시간 추천 아님:** KRX는 EOD(End of Day) 데이터이므로, 실시간 시세와 수급이 필요한 고급 전략에는 KIS 유지.

---

## 기술 사양

### 1) KRX OpenAPI

**엔드포인트**

```
GET https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd  (KOSPI 일별매매)
GET https://data-dbg.krx.co.kr/svc/apis/sto/ksq_bydd_trd  (KOSDAQ 일별매매)
```

**인증**

```http
Authorization 헤더 (HTTP 헤더 기반)
AUTH_KEY: <KRX API 키>
Accept: application/json
```

**요청 파라미터**

| 파라미터 | 설명 | 예시 |
|---------|------|------|
| `basDd` | 기준일 (YYYYMMDD) | `20240301` |

**응답 형식**

```json
{
  "OutBlock_1": [
    {
      "ISU_CD": "005930",
      "ISU_NM": "삼성전자",
      "MKT_NM": "유가증권",
      "TDD_CLSPRC": "70000",
      "CMPPREVDD_PRC": "1000",
      "FLUC_RT": "1.5",
      "TDD_OPNPRC": "69000",
      "HGPRC": "70500",
      "LWPRC": "68500",
      "ACC_TRDVOL": "5000000",
      "ACC_TRDVAL": "350000000000",
      "MKTCAP": "1500000000000",
      "LIST_SHRS": "21400000000"
    },
    ...
  ]
}
```

**주요 필드**

| 필드 | 설명 | 데이터형 | 사용처 |
|-----|------|---------|--------|
| `ISU_CD` | 종목코드 (6자리 단축코드) | str | symbol 매핑 |
| `TDD_CLSPRC` | 종가 | str(숫자) | price → int |
| `FLUC_RT` | 등락률 (%) | str(숫자) | change_rate → float |
| `ACC_TRDVOL` | 거래량 | str(숫자) | volume → int |

### 2) 토글: `RECOMMEND_DATA_SOURCE`

**설정**

```python
# backend/app/config.py

class Settings(BaseSettings):
    recommend_data_source: Literal["kis", "krx"] = "kis"  # 기본값
    krx_api_key: str = ""
```

**환경 변수**

```bash
# backend/.env

RECOMMEND_DATA_SOURCE=kis  # kis | krx
KRX_API_KEY=<secret>
```

### 3) KRX 모듈: `backend/app/stocks/krx.py`

**주요 함수**

```python
async def get_market_snapshot(
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, dict[str, Any]]:
    """
    KOSPI + KOSDAQ 스냅샷 병합.
    
    Returns:
        {symbol: {"price": int, "change_rate": float, "volume": int}}
    """
```

**특징**

1. **EOD 데이터:** 오늘 기준일부터 최대 7일 거슬러 올라가며 첫 거래일 데이터를 조회.
   - 장중이나 휴장일에는 당일 데이터가 없으므로 이전 거래일 사용.

2. **단일비행(Single-Flight):**
   - `asyncio.Lock`으로 동시 호출을 직렬화 (첫 요청만 API 타고 나머지는 대기).
   - 추천 스트리밍에서 다중 quote 요청이 들어와도 스냅샷은 1회만 조회.

3. **TTL 캐시:**
   - 하루 동안 스냅샷 캐시 (`_SNAPSHOT_TTL_SEC = 86400초`).
   - 기준일 키로 저장: `_snapshot_cache[resolved_basDd] = (timestamp, snapshot)`.

4. **병합:**
   - KOSPI + KOSDAQ 데이터를 하나의 dict로 병합.
   - 종목코드(`ISU_CD`) 중복 없음 (KOSPI와 KOSDAQ은 코드 범위가 다름).

### 4) 라우터: `app/routers/recommend.py`

**헬퍼 함수**

```python
async def _resolve_fns(settings) -> tuple[PriceFn, FlowFn]:
    """추천 시세 데이터 소스에 따라 price_fn/flow_fn 결정."""
    if settings.recommend_data_source == "krx":
        # 시세=KRX 스냅샷(lazy), 수급=KIS 일별 캐시(KRX 미제공)
        return krx_price_fn, get_investor_flow_daily
    else:
        # KIS (기본)
        return get_current_price, get_investor_flow
```

**통합**

- `GET /api/recommend/{theme}` 및 `/api/recommend/{theme}/stream` 에서 `_resolve_fns`를 호출.
- `price_fn`과 `flow_fn`을 `recommend_for_theme` / `stream_recommend_for_theme`에 주입.
- 기존 KIS 라우터는 변경 없음 (기본값).

---

## KRX vs. KIS: 비교

| 항목 | KIS | KRX |
|-----|-----|-----|
| **데이터 종류** | 실시간 시세 + 투자자 수급 | EOD(일별) 시세만 |
| **호출 비용** | rate limit (2건/초 paper, 16건/초 live) | 비교적 여유로움 |
| **종목 수** | 개별 조회 | KOSPI 948 + KOSDAQ 1822 (스냅샷) |
| **수급 정보** | KIS 직접 | **KRX 미제공 → KIS로 보완(일별 캐시)** |
| **추천 점수 구성** | momentum(40) + fundamental(35) + supply(25) | momentum(40) + fundamental(35) + supply(25) |
| **시세 실시간성** | 실시간 (장중) | EOD (직전 거래일) |
| **용도** | 실시간 모니터링, 실시간 매매 | 일일 추천, 배치 분석 |

### 수급 처리 (KRX 미제공 → KIS 보완)

KRX 일별매매에는 외국인/기관 순매수(수급)가 없다. 그래서 KRX 모드에서도 **수급만 KIS**로 조회한다.
- `rankings.get_investor_flow_daily`: 수급은 EOD(장 종료 후 1회 정산)이라 **종목별 하루 캐시**(`_FLOW_TTL_SEC=86400`) + 종목별 단일비행으로, 종목당 하루 1회만 KIS를 호출한다.
- 호출 비용: 모의 초당 2건 제한 → 분야 첫 로드 시 후보 30종목 ≈ 13.5초(이후 캐시로 즉시). 수급이 None(오류)이면 캐시하지 않고 다음에 재시도.
- 따라서 KRX 모드도 수급 점수가 정상 반영된다(전 종목 중립 아님).

### 시세 기준일 표기 (price_date)

KRX는 EOD라 추천 응답에 **시세 기준일(`price_date`, 거래일)** 을 재무 기준일(`base_date`, 분기)과 구분해 노출한다(`krx.get_resolved_date()`). 화면은 "시세 {거래일} · 재무 {분기}"로 표기.

---

## 구현 상세

### KRX 스냅샷 조회 흐름

1. **라우터 요청:**
   ```
   GET /api/recommend/semiconductor
   ```

2. **settings 확인:**
   ```python
   if settings.recommend_data_source == "krx":
       snapshot = await krx.get_market_snapshot(settings)
   ```

3. **Lock 진입 (_resolve_fns 내 krx_price_fn에서):**
   ```python
   async with _snapshot_lock:
       # 캐시 확인 (같은 날짜면 반환)
       # 캐시 미스: 7일 lookback으로 KOSPI 데이터 찾기
       # KOSPI 데이터 있으면 KOSDAQ도 같은 날짜로 조회
       # 병합: {symbol: {price, change_rate, volume}}
   ```

4. **price_fn 호출 (recommend_service._enrich_stock에서):**
   ```python
   snapshot_data = snapshot[symbol]  # dict 조회, 네트워크 없음
   return {
       "symbol": symbol,
       "price": snapshot_data["price"],
       "change_rate": snapshot_data["change_rate"],
       "volume": snapshot_data["volume"],
   }
   ```

5. **flow_fn 호출:**
   ```python
   # KRX 모드에서도 수급은 KIS로 조회(종목별 하루 캐시)
   return await get_investor_flow_daily(symbol)
   ```

### 스트리밍에서의 동작

**SSE `/api/recommend/{theme}/stream` 시퀀스:**

```
1. candidates 이벤트 발송 (즉시, 스냅샷 조회 전)
   └─ 후보 종목 목록 전달

2. 스냅샷 lazy 조회 (첫 quote 요청 시)
   └─ _enrich_stock → price_fn 호출 → 스냅샷 첫 조회 (캐시/락으로 1회)

3. quote 이벤트* (비동기, 완료 순서대로)
   └─ 각 종목 시세 스트리밍

4. result 이벤트 (모든 quote 완료 후)
   └─ 최종 점수 및 정렬 종목
```

**특징:**
- candidates는 지연되지 않음 (로컬 조회).
- 스냅샷 조회는 첫 quote 요청 시점에 발생 (가장 빠른 종목의 요청).
- 동시 호출 여러 개 들어와도 단일비행으로 스냅샷 1회만 조회.

---

## 테스트 전략

### 단위 테스트: `backend/tests/test_krx.py`

**respx mock 사용 (라이브 호출 안 함)**

1. `test_fetch_market_kospi_success` — KOSPI 정상 조회
2. `test_fetch_market_empty_response` — 빈 응답 처리
3. `test_get_market_snapshot_single_flight` — 동시 호출 1회만 네트워크 타는지 확인
4. `test_get_market_snapshot_lookback` — 빈 응답 날짜 건너뛰고 재시도
5. `test_snapshot_data_parsing` — 데이터 형식 검증 (int, float 정확성)
6. `test_snapshot_cache_hit` — 캐시 히트 시 추가 네트워크 없음
7. `test_missing_fields_parsed_as_none` — 필드 누락/파싱 오류 → None

### 통합 테스트: `backend/tests/test_recommend_router.py` (추가)

1. `test_krx_시세_소스_토글` — `RECOMMEND_DATA_SOURCE=krx` 시 KRX 스냅샷 사용 확인
2. `test_krx_수급은_중립` — KRX 모드에서 수급 점수 = 50.0 (중립)
3. `test_kis_소스_기본값` — 기본값: KIS 사용

---

## 향후 확장

### 수급 정보 추가 (외국인/기관)

KRX에서 제공하는 별도 API:
- 투자자 매수/매도 현황 API (투자자별, 시장별, 기간별)
- 현재 구현: 생략 (시기상 추가 가능)

**추가 시:**
```python
# krx.py에 함수 추가
async def get_investor_flow(symbol: str) -> dict:
    """KRX 투자자 수급 조회"""
    # 별도 API 호출
```

**라우터 수정:**
```python
async def krx_flow_fn(symbol: str):
    return await krx.get_investor_flow(symbol)  # 중립 대신 실제 수급
```

---

## 사용 예시

### 1. KRX로 토글

```bash
# backend/.env
RECOMMEND_DATA_SOURCE=krx
KRX_API_KEY=your_krx_api_key
```

**재부팅 후:**
```bash
python -m uvicorn app.main:app --reload
```

**요청:**
```bash
curl http://localhost:8000/api/recommend/semiconductor
```

**응답 (KRX 시세 포함):**
```json
{
  "data": {
    "theme": "semiconductor",
    "base_date": "20240301",
    "items": [
      {
        "symbol": "005930",
        "name": "삼성전자",
        "price": 70000,
        "change_rate": 1.5,
        "volume": 5000000,
        "supply": 50.0,
        "score": 75.3
      },
      ...
    ]
  }
}
```

### 2. KIS로 되돌리기

```bash
# backend/.env
RECOMMEND_DATA_SOURCE=kis
```

---

## 주의점 & 제약

1. **시크릿 관리:**
   - `KRX_API_KEY`는 `.env` 파일에만 저장, git 커밋 금지.
   - `backend/.env.example`에는 예시만 기록.

2. **EOD 데이터:**
   - KRX는 일별매매만 제공 (실시간 아님).
   - 장중 조회 시 전일 또는 이틀 전 데이터 사용.

3. **수급(KRX 미제공 → KIS 보완):**
   - KRX 일별매매엔 외국인/기관 수급이 없어, KRX 모드에서도 수급은 KIS로 조회한다.
   - 종목별 하루 캐시(`get_investor_flow_daily`)로 종목당 하루 1회만 호출(EOD 정산).
   - 모의 초당 2건 제한 → 분야 첫 로드만 십수 초, 이후 캐시로 즉시.

4. **스냅샷 크기:**
   - KOSPI 948 + KOSDAQ 1822 = 약 2770종목 데이터.
   - 메모리 사용: 약 1~2MB (큰 문제 없음).
   - 캐시 기간: 하루 (자동 갱신).

5. **에러 처리:**
   - KRX API 호출 실패 시 빈 dict 반환 (추천 결과 공백).
   - 라우터에서 try/except로 처리 (graceful degradation).

---

## 동기화: 문서 참고

- `docs/06-recommend.md` — 분야별 추천 설계 및 점수 로직.
- `docs/02-specs.md` — 기술 스택 및 환경 변수.
- 라우터 관련: `app/routers/recommend.py` 코멘트 참조.

---

## 검증

```bash
# 전체 테스트 실행
pytest backend/tests/test_krx.py -v
pytest backend/tests/test_recommend_router.py::test_krx_시세_소스_토글 -v
pytest backend/tests -q  # 전체 통과 확인
```

**예상 결과:**
```
test_krx.py::test_fetch_market_kospi_success PASSED
test_krx.py::test_get_market_snapshot_single_flight PASSED
test_krx.py::test_snapshot_data_parsing PASSED
test_recommend_router.py::test_krx_시세_소스_토글 PASSED
test_recommend_router.py::test_krx_수급은_중립 PASSED
... (총 전체 테스트 통과)
```

---

## 변경 내역

| 파일 | 변경 | 설명 |
|-----|------|------|
| `app/config.py` | 추가 | `recommend_data_source`, `krx_api_key` |
| `app/stocks/krx.py` | 신규 | KRX 스냅샷 조회, 캐시, 단일비행 |
| `app/routers/recommend.py` | 수정 | `_resolve_fns` 헬퍼 추가, 라우터 통합 |
| `backend/.env.example` | 추가 | 환경 변수 예시 |
| `tests/test_krx.py` | 신규 | respx 모의 테스트 |
| `tests/test_recommend_router.py` | 추가 | KRX 토글 테스트 |

