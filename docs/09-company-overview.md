# 09-company-overview.md — 기업개요 탭 (네이버금융 스크래핑)

> 종목 차트 모달(`ChartModal`)에 **"기업개요" 탭**을 추가해, 네이버금융 종목분석의
> 기업개요를 보여준다. 차트(일/주/분봉)와 같은 모달에서 탭으로 전환한다.

## 1. 목표 / 범위

- 차트 모달에 일봉/주봉/분봉과 나란히 **기업개요** 탭 추가.
- 정보 제공용(자동매매와 무관). 회사 개요 요약 불릿 + 기준일 표시.

## 2. 데이터 출처 (스크래핑)

네이버금융 종목분석 기업개요 탭은 **WiseReport iframe**을 임베드한다.

- URL: `https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={종목코드}`
- 인코딩: **UTF-8**. 서버사이드(httpx)로 조회 가능.
- 구조(파싱 대상):
  - 기준일: `[기준:YYYY.MM.DD]`
  - 개요 불릿: `<div class="cmp_comment"><ul class="dot_cmp"><li class="dot_cmp">…</li>…</ul></div>`
  - (이 페이지에서 `<li class="dot_cmp">`는 기업개요 불릿만 해당 — 펀더멘털 섹션은 다른 구조)

> **주의**: 스크래핑이라 네이버/WiseReport HTML 구조 변경 시 깨질 수 있다. 깨져도 앱은
> 정상 동작(빈 개요로 graceful)하며, 구조 변경 시 `naver.py`의 정규식만 고치면 된다.
> ToS상 개인 참고용. 하루 캐시로 호출을 최소화한다.

## 3. 백엔드 (`app/stocks/naver.py` + `app/routers/company.py`)

- `get_company_overview(symbol)` → **두 WiseReport 페이지를 동시 조회(`asyncio.gather`)** 해 파싱:
  - `c1010001.aspx`: 기업개요 불릿·시세·주주현황·기준일
  - `c1020001.aspx`: 최근연혁·주요제품 매출구성
  ```
  { "symbol", "base_date": "YYYY.MM.DD"|null,
    "summary": [str, ...],                          # 기업개요 불릿(<li class="dot_cmp">)
    "price":   [{"label","value"}, ...],            # 시세정보(<table id="cTB11">)
    "shareholders": [{"name","shares","pct"}, ...],  # 주주현황(<tr class="p_sJJ..">, title=주주명)
    "products": [{"name","pct"}, ...],              # 주요제품 매출구성(<table id="cTB203">)
    "history":  [{"date","detail"}, ...] }          # 최근연혁(<table id="cTB202">)
  ```
  - 표는 **행 단위로 첫 th/td**를 뽑아 헤더 행을 자동 제외. 정규식 + stdlib `html.unescape`(새 의존성 없음).
  - **종목별 하루 캐시(`_OVERVIEW_TTL_SEC=86400`) + 단일비행(Lock)**. 다 비면 캐시 안 함(재시도).
  - 각 페이지 독립 graceful(한 페이지 실패해도 다른 페이지 데이터는 반환).
- 엔드포인트: `GET /api/company/{symbol}/overview` → `{ "data": {...} }`.

## 4. 프론트 (`components/ChartModal.tsx`)

- 탭 상태 `tab: "overview" | "daily" | "weekly" | "minute"`. **기업개요가 첫 탭이자 기본 선택**(모달 열면 기업개요부터 표시).
- `tab === "overview"`이면 차트 대신 **개요 불릿 → 최근연혁 → 주요제품 매출구성 → 시세 → 주주현황 표** 순서로 표시(기준일·출처 표기).
- `fetchOverview` prop 주입(`App`이 `getCompanyOverview` 전달, 테스트 주입 가능).
- 차트 데이터 조회/렌더 effect는 `overview` 탭일 때 건너뛴다(불필요한 호출·렌더 방지).

## 5. 테스트

- 백엔드(`test_naver.py`): respx mock으로 파싱(불릿·기준일), HTTP 오류→빈 결과, 캐시 재호출 차단.
- 프론트(`ChartModal.test.tsx`): 기업개요 탭 클릭→`fetchOverview` 호출 + 개요·기준일 표시.
- 라이브 검증: `GET /api/company/005930/overview` → 삼성전자 개요 3줄(2026.06.02 기준), 브라우저 탭 표시 확인.
