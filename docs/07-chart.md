# 07 — 종목 차트 (일봉/주봉/분봉 모달)

> 관심종목을 클릭하면 모달 팝업으로 캔들차트(일봉/주봉/분봉 토글)를 보여준다.
> 설계 결정: 차트 종류=**일봉/주봉/분봉 토글**, 렌더=**lightweight-charts**(의존성 승인됨),
> 위치=**모달 팝업**. 읽기 순서상 `06-recommend.md` 다음의 보강 기능 문서.

## 1. 목표 / 범위

- 관심종목 행 클릭 → 해당 종목 캔들차트 모달.
- 일봉(최근 ~100영업일)과 분봉(당일)을 토글로 전환.
- 정보 제공용. 자동매매와 무관(주문 트리거 아님).
- MVP: 캔들 + 거래량. 보조지표(MA/RSI 오버레이)는 후속.

## 2. KIS API (모드 무관 — 시세 데이터)

| 종류 | URL | TR_ID | 핵심 응답(output2[]) |
|------|-----|-------|----------------------|
| 일봉 | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` | `FHKST03010100` | `stck_bsop_date·stck_oprc·stck_hgpr·stck_lwpr·stck_clpr·acml_vol` |
| 분봉 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` | `FHKST03010200` | `stck_bsop_date·stck_cntg_hour·stck_oprc·stck_hgpr·stck_lwpr·stck_prpr·cntg_vol` |

- 일봉 요청 파라미터: `FID_COND_MRKT_DIV_CODE=J`, `FID_INPUT_ISCD`, `FID_INPUT_DATE_1`(시작), `FID_INPUT_DATE_2`(종료, 1회 최대 100개), `FID_PERIOD_DIV_CODE=D`, `FID_ORG_ADJ_PRC=1`(원주가).
- 분봉 요청 파라미터: `FID_COND_MRKT_DIV_CODE=J`, `FID_INPUT_ISCD`, `FID_INPUT_HOUR_1`(HHMMSS, 조회 종료시각), `FID_PW_DATA_INCU_YN=Y`, `FID_ETC_CLS_CODE=""`.
  - KIS 분봉은 **지정 시각 기준 직전 30분**만 반환한다. 정규장(09:00~15:30 KST) 밖에서 현재 시각으로 조회하면 장외 평탄 구간만 잡히므로, **정규장 밖이면 `FID_INPUT_HOUR_1`을 `153000`(장 마감)으로 고정**해 마지막 거래 세션의 실제 분봉을 가져온다.
- 일봉 종가는 `stck_clpr`, 분봉 종가는 `stck_prpr`. 거래량은 일봉 `acml_vol`(당일 누적=일거래량), 분봉 `cntg_vol`(분 체결량).
- **유연한 파싱**: 시가/고가/저가가 누락된 경우 종가를 기준으로 캔들을 최대한 복구하여 표시한다.

## 3. 백엔드 (`app/kis/charts.py` + `app/routers/charts.py`)

- `get_daily_chart(symbol)` / `get_weekly_chart(symbol)` / `get_minute_chart(symbol)` → 캔들 리스트(시간 오름차순).
- 응답 캔들: `{ "time", "open", "high", "low", "close", "volume" }`.
  - 일봉 `time` = `"YYYY-MM-DD"`(lightweight-charts business day).
  - 분봉 `time` = UNIX 초. **KST 벽시계 숫자를 UTC로 환산**해 차트 축이 KST HH:MM을 그대로 표시하게 한다.
- **일시 오류와 '데이터 없음'을 구분한다(중요).**
  - KIS 일시 오류(`httpx.HTTPError`, 또는 HTTP 200이라도 `rt_cd != "0"`) → `ChartUnavailableError`를 던진다.
  - 라우터가 이를 잡아 **503 `CHART_UNAVAILABLE`**로 응답한다(빈 캔들 200으로 위장하지 않음).
  - 정상 응답(`rt_cd == "0"`)인데 데이터가 없을 때만 빈 리스트(`[]`)를 반환한다(진짜 '데이터 없음').
  - 배경: 초당 거래건수 초과(`EGW00201`)는 HTTP 200 + `rt_cd != "0"`로 와서, 예전엔 빈 캔들로 둔갑해
    "차트 데이터가 없습니다"가 간헐적으로 떴다. 이제 `KisClient`가 본문 `msg_cd`를 보고 레이트리밋을
    지수 백오프로 재시도하고, 그래도 실패하면 503으로 분리한다(모든 KIS 호출 공통).
- 엔드포인트: `GET /api/charts/{symbol}?interval=daily|weekly|minute` → `{ "data": { "symbol", "interval", "candles": [...] } }`.
- 봉별 날짜 범위는 서버에서 산출(종료=오늘 KST). **일봉**은 시작=오늘−200일(≈100영업일),
  **주봉**은 시작=오늘−730일(≈2년·~100주). KIS 1회 응답 100건 상한에 맞춰 봉별 lookback을 분리한다
  (같은 1회 호출이라 건수가 늘어도 속도 영향은 사실상 없음 — 라운드트립이 지배).
- **차트 캐시(성능)**: `(symbol, interval)`별로 캔들을 메모리 캐시한다(단일비행 Lock). 모달 재오픈·탭 전환마다
  KIS를 재호출하지 않는다. TTL은 시장 시간대에 맞춘다 — 일/주봉 장중 60초·분봉 장중 30초, **장외 30분**
  (장외엔 데이터 고정). 빈 결과/오류는 캐시하지 않아 다음 호출에서 재시도한다. `clear_chart_cache()`로 비운다.
  효과: 캐시 히트 시 ~3000ms+ → ~25ms.

## 4. 프론트 (`components/ChartModal.tsx`)

- 라이브러리: **lightweight-charts**(승인된 의존성). 캔들 시리즈 + 거래량 히스토그램.
- 관심종목 `WatchList` 행을 클릭 가능(button)으로 만들고 `onSelect(symbol, name)` 호출.
- `App`이 `chartTarget` 상태로 모달 표시. 모달 안에서 일봉/주봉/분봉 토글 버튼.
- **로딩 안정성**: 조회 실패(503 등) 시 사용자 개입 없이 **1회 자동 재시도**한다(`AUTO_RETRY_DELAY_MS=600`).
  재시도 사이에는 `loading`을 유지해 "데이터 없음" 빈상태가 깜빡이지 않게 한다. 자동 재시도까지
  실패하면 **[다시 시도]** 버튼(수동 재요청)을 노출한다. 자동 재시도는 `symbol`/`interval` 1건당 1회.
- 닫기: X 버튼, 배경 클릭, Esc. 접근성: `role="dialog"`, `aria-modal`, 포커스/Esc 처리.
- 일시 오류 시 "차트 데이터를 불러올 수 없습니다", 진짜 빈 데이터 시 "차트 데이터가 없습니다" 안내(구분).
- 상승=빨강/하락=파랑(국내 관례) 색상 토큰 적용.
- **탭 메모(성능)**: 이미 받은 캔들을 탭(interval)별로 `useRef` Map에 메모해, 탭을 다시 눌러도
  재조회하지 않는다(네트워크 0). 종목이 바뀌면 메모를 비운다. 빈 결과는 메모하지 않는다.

## 5. 테스트

- 백엔드: 일봉/주봉/분봉 파싱(respx mock), 오류 구분(500·`rt_cd≠0`→`ChartUnavailableError`, `rt_cd=0`+빈데이터→`[]`),
  라우터 종단(`interval` 분기·잘못된 interval 400·일시 오류 503), `KisClient`의 `EGW00201` 재시도(`test_client.py`).
- 프론트: `lightweight-charts`는 jsdom canvas 미지원이라 **모듈 모킹**. ChartModal의 토글/닫기/빈상태 로직과 WatchList 클릭→`onSelect(symbol, name)` 호출을 검증.

## 6. 안전/성능

- 차트는 읽기 전용. 모달 열 때 1회 조회(분봉/일봉 토글 시 각 1회, 단 캐시·탭 메모로 재호출 최소화). 폴링 없음.
- 분봉은 직전 30분 윈도. 장 마감 후/주말에는 조회 시각을 장 마감(15:30)으로 고정해 마지막 세션 분봉을 보여준다. 빈 결과는 안내로 처리.
- **KIS 호출 baseline**: 모든 KIS REST 호출은 앱 lifespan이 만든 **keep-alive 공유 httpx 클라이언트**
  (`app/kis/client.py`의 `_shared_client`)를 재사용한다. 요청마다 새 클라이언트를 만들 때 발생하던
  TCP+TLS 핸드셰이크를 제거해 콜드 호출 지연을 줄인다(테스트는 공유 클라이언트 미등록 → 요청별 생성으로 동작).
- 측정(모의투자): 캐시 히트 ~25ms, 콜드 단일 ~250~500ms, (개선 전) 동시/연속 경합 시 3000~7000ms.
- **폴링 경합 제거(중요)**: 대시보드는 5초마다 잔고·포지션 등을 폴링(KIS 호출)한다. 이 버스트가
  차트 조회와 0.45초 레이트게이트 슬롯을 두고 경합하면 차트가 느려진다. 그래서 `App`의 폴링은
  **대시보드 탭이 보일 때(추천 탭·백그라운드 제외)만** 돌고, **차트 모달이 열려 있는 동안에는 멈춘다**
  (모달을 닫으면 즉시 1회 갱신 후 재개). 모달 중 KIS 슬롯을 차트가 독점해 콜드 지연이 ~RTT로 수렴한다.
- **잔고·포지션 중복 호출 통합**: 잔고 요약과 포지션이 동일한 `inquire-balance`(output1=보유, output2=요약)를
  각각 호출하던 것을 `_get_balance_raw`(짧은 TTL 2초 + 단일비행)로 묶어 **5초 폴링이 KIS를 1회만** 부른다.
  대시보드를 켜둔 상태(모달 미오픈)에서도 폴링 KIS 부하가 2→1로 줄어 경합이 추가로 완화된다.
