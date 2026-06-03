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
- 일봉 날짜 범위는 서버에서 산출(종료=오늘 KST, 시작=오늘−200일 ≈ 100영업일 확보).

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

## 5. 테스트

- 백엔드: 일봉/주봉/분봉 파싱(respx mock), 오류 구분(500·`rt_cd≠0`→`ChartUnavailableError`, `rt_cd=0`+빈데이터→`[]`),
  라우터 종단(`interval` 분기·잘못된 interval 400·일시 오류 503), `KisClient`의 `EGW00201` 재시도(`test_client.py`).
- 프론트: `lightweight-charts`는 jsdom canvas 미지원이라 **모듈 모킹**. ChartModal의 토글/닫기/빈상태 로직과 WatchList 클릭→`onSelect(symbol, name)` 호출을 검증.

## 6. 안전/성능

- 차트는 읽기 전용. 모달 열 때 1회 조회(분봉/일봉 토글 시 각 1회). 폴링 없음.
- 분봉은 당일 데이터만(장 마감 후/주말 제한적) — 빈 결과는 안내로 처리.
