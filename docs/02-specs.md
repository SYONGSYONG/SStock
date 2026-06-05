# 02-specs.md — 기술 명세

## 기술 스택 (확정)

| 레이어 | 기술 | 비고 |
|--------|------|------|
| 백엔드 | Python 3.12+ / FastAPI | 비동기 API + 봇 엔진 |
| 비동기 런타임 | asyncio | 봇 엔진을 백그라운드 태스크로 구동 |
| HTTP 클라이언트 | httpx (async) | KIS REST 호출 |
| 웹소켓 | websockets | KIS 실시간 시세 구독 |
| 데이터 처리 | pandas | 지표 계산(이동평균·RSI) |
| 검증 | Pydantic v2 | 설정·요청·응답 스키마 검증 |
| 데이터베이스 | SQLite (aiosqlite 또는 sqlite3) | 파일 기반, WAL 모드 |
| 설정 | pydantic-settings + `.env` | 환경변수 로드 |
| 프론트엔드 | React 19 + TypeScript (Vite) | 실시간 대시보드 |
| 차트 | lightweight-charts 또는 recharts | 시세·지표 시각화 |
| 백엔드 테스트 | pytest + pytest-asyncio + respx | API·전략 단위/통합 테스트 |
| 프론트 테스트 | Vitest + React Testing Library | 컴포넌트 테스트 |

> 의존성은 절대규칙 2(돌발 의존성 금지)에 따라 추가 전 사용자 승인을 받는다.

---

## KIS API 도메인

| 구분 | 모의투자 (기본) | 실전 |
|------|----------------|------|
| REST | `https://openapivts.koreainvestment.com:29443` | `https://openapi.koreainvestment.com:9443` |
| WebSocket | `ws://ops.koreainvestment.com:31000` | `ws://ops.koreainvestment.com:21000` |

> `TRADING_MODE`에 따라 도메인과 TR_ID 접두사(모의 `V…` / 실전 `T…`)를 전환한다.

---

## 사용 KIS API 목록 (MVP)

명세 출처: `Reference/API_DOC/`. 각 API는 `tr_id`로 식별된다.

### 인증 (OAuth)

| 기능 | URL | Method | 비고 |
|------|-----|--------|------|
| 접근토큰 발급 | `/oauth2/tokenP` | POST | access_token(24h, 6h 내 재호출 시 기존값) |
| 접근토큰 폐기 | `/oauth2/revokeP` | POST | |
| 웹소켓 접속키 | `/oauth2/Approval` | POST | approval_key 발급 |

### 시세 (REST)

| 기능 | URL | TR_ID |
|------|-----|-------|
| 주식현재가 시세 | `/uapi/domestic-stock/v1/quotations/inquire-price` | FHKST01010100 |
| 호가/예상체결 | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` | FHKST01010200 |
| 당일 분봉 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` | FHKST03010200 |
| 기간별 시세(일/주/월/년) | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` | FHKST03010100 |

### 실시간 (WebSocket)

| 기능 | TR_ID (실전/모의) |
|------|------------------|
| 실시간 체결가 | H0STCNT0 / H0STCNT0 |
| 실시간 호가 | H0STASP0 / H0STASP0 |
| 실시간 체결통보 | H0STCNI0 / H0STCNI9 |

**자동 재연결(견고화):** KIS 웹소켓은 유휴·서버측·토큰·네트워크 사유로 수시로 끊긴다.
`KisRealtimeClient.run()`은 **봇이 켜져 있는 한(`_stop` 전까지) 무한 재연결**한다. 끊김/오류 시
지수 백오프(상한 30초)로 재시도하되, **연결이 너무 빨리 끊기면(<5초) 백오프를 키우고 오래
유지되면 리셋**해 재연결 폭주를 막는다. 과거에는 `max_retries=5`로 **5회 실패 후 영구 정지**하는
결함이 있어 시세가 조용히 꺼졌다(→ 워밍업·국면 분류 중단). 연결됨/끊김 전환은 **감사 로그
(`MARKET`)로 가시화**한다. `MarketDataService.running`은 이 태스크가 살아있는지로 판정하므로,
무한 재연결 동안 `market_running`은 `true`를 유지한다.

### 주문/계좌 (REST)

| 기능 | URL | TR_ID (실전 → 모의) |
|------|-----|---------------------|
| 주식주문(현금) | `/uapi/domestic-stock/v1/trading/order-cash` | 매수 TTTC0012U→VTTC0012U, 매도 TTTC0011U→VTTC0011U |
| 주문 정정/취소 | `/uapi/domestic-stock/v1/trading/order-rvsecncl` | TTTC0013U→VTTC0013U |
| 매수가능조회 | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` | TTTC8908R→VTTC8908R |
| 주식잔고조회 | `/uapi/domestic-stock/v1/trading/inquire-balance` | TTTC8434R→VTTC8434R |
| 일별주문체결조회 | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` | TTTC0081R→VTTC0081R |

> 매도가능수량조회·실현손익 등 일부 API는 **모의투자 미지원** — 모의 모드에서는 대체 로직(잔고조회 기반) 사용.

### 대시보드 계좌 잔고 API

| 엔드포인트 | 설명 | 출처 |
|-----------|------|------|
| `GET /api/account/balance` | 계좌 잔고 요약(예수금·주문가능현금·총평가·평가손익·순자산) | 주식잔고조회 `output2` |
| `GET /api/positions` | 계좌 보유 포지션(수량·평단·현재가·평가금액·손익·손익률) | 주식잔고조회 `output2` |

- `/api/positions` 는 `inquire-balance` 기준의 보유 잔고만 반환한다. 요청 주문 수량은 포지션에 포함하지 않는다.
- 주문 체결 상태는 `inquire-daily-ccld` 결과로 로컬 주문 상태를 보정한다.

- 응답: `{ "data": { "mode", "available", "deposit", "orderable_cash", "purchase_amount", "eval_amount", "eval_pnl", "total_eval", "net_asset" } }`.
- 필드 매핑(`output2`): `dnca_tot_amt`(예수금)·`prvs_rcdl_excc_amt`(가수도정산≈주문가능현금)·`pchs_amt_smtl_amt`(매입합계)·`evlu_amt_smtl_amt`(평가합계)·`evlu_pfls_smtl_amt`(평가손익)·`tot_evlu_amt`(총평가)·`nass_amt`(순자산).
- **graceful**: KIS 일시 오류(예: 토큰 만료 `EGW00121`, 모의서버 500) 시 500 대신 `available=false` + 모든 값 `null`로 응답 → 대시보드가 깨지지 않는다(시세 조회와 동일 정책).
- **지연 특성**: 잔고는 로컬 DB 패널(~0.23s)과 달리 **매 폴링마다 KIS REST 왕복**이 있어 ~0.5s 걸린다. 두 가지로 체감 지연을 줄인다.
  - **토큰 프리워밍**(`KIS_TOKEN_PREWARM=true`, 기본): 기동 시 토큰을 미리 확보해 첫 호출의 발급 왕복 제거(파일 캐시 유효 시 네트워크 없음, 실패해도 기동 계속).
  - **로딩 상태 분리**: 프론트 `AccountPanel`은 첫 조회 전(`null`)엔 "불러오는 중…", KIS 오류(`available=false`)일 때만 "조회 불가"를 표시(에러처럼 보이는 깜빡임 제거).

### 대시보드 차트 API

| 엔드포인트 | 설명 | 출처 |
|-----------|------|------|
| `GET /api/charts/{symbol}?interval=daily\|weekly\|minute` | 일봉(최근 ~100영업일)/주봉(최근 ~100주)/분봉(당일) 캔들 | 기간별시세 `FHKST03010100` / 당일분봉 `FHKST03010200` |

- 응답: `{ "data": { "symbol", "interval", "candles": [ { "time", "open", "high", "low", "close", "volume" } ] } }` (시간 오름차순).
- 일봉/주봉 `time`=`"YYYY-MM-DD"`, 분봉 `time`=UNIX 초(KST 벽시계→UTC 환산). KIS 오류 시 빈 캔들 graceful.
- 상세 설계: `docs/07-chart.md`.

---

## 인증 흐름

```
1. appkey + appsecret → POST /oauth2/tokenP → access_token (24h)
   - 토큰은 메모리/파일 캐시, 만료 전 갱신. 6h 내 재요청 시 기존 토큰 반환됨에 유의
2. REST 요청 헤더:
   authorization: Bearer <access_token>
   appkey, appsecret, tr_id, custtype=P
3. WebSocket:
   POST /oauth2/Approval → approval_key
   웹소켓 핸드셰이크 시 approval_key 사용
```

## KIS 클라이언트 안정성 강화 전략

KIS API의 초당 호출 제한(TPS) 및 일시적 네트워크 불안정에 대응하기 위해 `KisClient`에 다음과 같은 전략을 적용한다.

| 전략 | 내용 | 목적 |
|------|------|------|
| **레이트리미터 (사전 억제)** | 전역으로 호출 간 최소 간격(`KIS_MIN_CALL_INTERVAL_SEC`, 기본 paper 0.45s/live 0.06s)을 강제 | 초당 거래건수 초과(EGW00201) **사전** 방지 |
| **동시성 제어 (Semaphore)** | 전역 세마포어(`asyncio.Semaphore(3)`)로 동시 호출 수 제한 | TPS 초과 방지 및 서버 부하 조절 |
| **지수 백오프 재시도** | 429, 503, 5xx, 네트워크 오류 시 최대 3회 재시도 (0.5s → 1s → 2s) | 일시적 오류 자동 복구 및 성공률 제고 |
| **EGW00201 본문 재시도** | HTTP 200이라도 본문 `rt_cd≠0`+`msg_cd=EGW00201`이면 백오프 재시도 | 상태코드로 안 드러나는 레이트리밋 사후 복구 |
| **토큰 자동 갱신** | 401 Unauthorized 발생 시 즉시 토큰 무효화 후 1회 재시도 | 만료 토큰으로 인한 실패 방지 |
| **Graceful 응답** | KIS 최종 실패 시 시세/잔고는 빈 데이터, **차트는 예외→503**으로 구분 | 일시 오류와 '데이터 없음' 혼동 방지 |

---

## 지표 계산 · 전략 엔진 성능

전략 엔진의 구조(무상태 `on_tick`), 지표 계산(`rolling_sma`/`to_tick_bars`/`closed_ticks`),
틱봉·확정봉, 신호 중복 억제, 그리고 향후 **틱당 O(1) 상태유지(stateful) Rolling SMA** 전환
계획은 전략 단일 문서로 이관했다 → **[11-strategy.md](11-strategy.md)** 참고.

---

## 데이터베이스 스키마 (초안)

> WAL 모드 활성화. 상세는 구현 단계에서 마이그레이션으로 확정.

```sql
-- 관심종목
CREATE TABLE watchlist (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL UNIQUE,      -- 종목코드 6자리
  name        TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 전략 설정 (종목별)
CREATE TABLE strategy_config (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,             -- 'ma_cross' | 'rsi_ma' (전략 상세: 11-strategy.md)
  params      TEXT NOT NULL,             -- JSON (기간, 기준선 등)
  enabled     INTEGER NOT NULL DEFAULT 0,
  max_qty     INTEGER,                   -- 종목당 최대 수량
  max_amount  INTEGER,                   -- 종목당 최대 금액
  UNIQUE(symbol, strategy)
);

-- 신호 로그 (집행과 분리)
CREATE TABLE signals (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol      TEXT NOT NULL,
  strategy    TEXT NOT NULL,
  side        TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  price       REAL,
  reason      TEXT,                      -- 신호 근거(지표값)
  mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),  -- 모드별 분리
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 주문/체결
CREATE TABLE orders (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_id   INTEGER REFERENCES signals(id),
  symbol      TEXT NOT NULL,
  side        TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  qty         INTEGER NOT NULL,
  price       REAL,
  mode        TEXT NOT NULL CHECK(mode IN ('paper','live')),
  kis_order_no TEXT,                     -- KIS 주문번호
  status      TEXT NOT NULL,             -- requested|filled|cancelled|rejected
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 시스템/감사 로그 (변경 불가)
CREATE TABLE audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  category    TEXT NOT NULL,             -- BOT|ORDER|SIGNAL|MODE|RISK|ERROR
  message     TEXT NOT NULL,
  mode        TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),  -- 모드별 분리
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 종목별 자본 칸막이(모드별 원금 한도)
CREATE TABLE capital_envelope (
  symbol     TEXT NOT NULL,
  principal  INTEGER NOT NULL,
  mode       TEXT NOT NULL DEFAULT 'paper' CHECK(mode IN ('paper','live')),
  PRIMARY KEY(symbol, mode)
);

-- 일일 주문 한도(모드별). 행이 없으면 환경변수 DAILY_MAX_* 기본값을 사용.
-- 대시보드에서 런타임에 조회·변경 가능(상수가 아니라 DB에 저장).
CREATE TABLE risk_limit (
  mode        TEXT NOT NULL PRIMARY KEY CHECK(mode IN ('paper','live')),
  max_orders  INTEGER NOT NULL,         -- 일일 최대 주문 횟수
  max_amount  INTEGER NOT NULL          -- 일일 최대 주문 금액(원)
);
```

---

## 환경 변수 목록

```env
# .env.example

# 실행 환경
APP_ENV=development

# 거래 모드 — paper(기본) | live. live는 명시적 전환만.
TRADING_MODE=paper

# KIS 인증 (절대 git 커밋 금지)
# 모의/실전은 각자 별도 앱키·시크릿·계좌(폴백 없음). 쓸 모드의 세트만 채운다.
KIS_PAPER_APP_KEY=       # 모의투자 앱키
KIS_PAPER_APP_SECRET=    # 모의투자 시크릿
KIS_PAPER_ACCOUNT_NO=    # 모의 종합계좌번호 8자리
KIS_LIVE_APP_KEY=        # 실전투자 앱키
KIS_LIVE_APP_SECRET=     # 실전투자 시크릿
KIS_LIVE_ACCOUNT_NO=     # 실전 종합계좌번호 8자리
KIS_ACCOUNT_PRODUCT=01   # 계좌상품코드 2자리 (모의/실전 공용)
KIS_TOKEN_PREWARM=true   # 기동 시 토큰 프리워밍(첫 시세/잔고 호출 지연↓). 테스트는 conftest가 off
KIS_MIN_CALL_INTERVAL_SEC=  # KIS 호출 간 최소 간격(초). 비우면 모드별 기본(paper 0.45/live 0.06). 테스트는 0

# 서버
HOST=127.0.0.1
PORT=8000

# 안전 가드 (DB의 risk_limit 행이 없을 때 쓰는 기본값. 대시보드에서 런타임 변경 가능)
DAILY_MAX_ORDERS=100     # 일일 최대 주문 횟수(기본값)
DAILY_MAX_AMOUNT=1000000 # 일일 최대 주문 금액(원, 기본값)

# 데이터베이스
DATABASE_PATH=./data/sstock.db
```

---

## 안전 가드 구현 명세

| 가드 | 동작 | 위치 |
|------|------|------|
| 모드 분리 | `TRADING_MODE`로 도메인·TR_ID 전환. live는 부팅 시 경고 + 대시보드 확인 필요 | config |
| 봇 정지 기본값 | 부팅 시 봇 OFF. 시작 토글 전 신규 주문 차단 | 봇 엔진 |
| 일일 한도 | 주문 전 당일 주문 횟수·금액 합산 검사(**매수·매도 모두 포함**), 초과 시 거부. 한도는 `risk_limit`(모드별)에서 읽고, 행이 없으면 `DAILY_MAX_*` 기본값. 대시보드에서 사용량 확인·한도 변경 가능(변경 시 재확인) | risk_guard / risk_limit_service |
| 미보유 매도 차단 | 봇은 자기 주문으로 보유한 수량까지만 매도(직접 매수 기보유분 보호). 매도가능 수량이 0이면 봇이 **신호 단계에서 주문을 만들지 않는다**(거절 주문 폭증 방지). 직접 호출 시엔 가드가 `NO_BOT_HOLDING`으로 거부 | trading_bot / risk_guard |
| 거절 주문 비저장 | 가드(`RiskError`)에서 막힌 주문은 **KIS로 전송되지 않으므로 `orders`에 남기지 않는다**(감사 로그 `RISK`에만 사유 기록). 실제 KIS 전송 후 거부된 주문만 `orders`에 `rejected`로 남는다 → 주문 내역 = 실제 주문만 | trading_bot |
| 신호 중복 억제 | 전략은 **확정봉만 평가**(진행 중 미완성 틱봉 제외 → 매 틱 재샘플링 휘프소 제거) + 봇은 **직전과 같은 방향 신호를 억제** → 교차 1회당 신호 1건 | indicators / trading_bot |
| 자본 칸막이 | 미등록 종목은 매수·매도 모두 금지. 매수 한도 = 원금 + min(0, 실현손익) — 실현이익은 한도 미반영(보수적), 실현손실만 한도 축소(안전). 실현이익은 정보로만 표시 | risk_guard / budget_service |
| 중복 주문 방지 | 신호 ID당 1주문. 처리된 신호 재집행 차단 | 주문 서비스 |
| 시크릿 미노출 | 에러·로그에 key/secret/token 마스킹 | 로깅 |

---

## 테스트 전략

| 대상 | 도구 | 핵심 케이스 |
|------|------|-----------|
| 전략 엔진 | pytest + pandas | 이동평균 크로스·RSI 신호 생성 정확성, 경계값 |
| KIS 클라이언트 | pytest + respx (HTTP mock) | 토큰 발급·갱신, 헤더 구성, 모드별 TR_ID/도메인 |
| 안전 가드 | pytest | 일일 한도 초과 거부, 봇 정지 시 주문 차단, 중복 신호 차단, 미보유 매도 차단(`NO_BOT_HOLDING`) |
| 일일 한도 조회·변경 | pytest | `risk_limit` 미설정 시 기본값 폴백, 설정/조회 왕복, 당일 사용량 집계 |
| 주문 흐름 | pytest-asyncio | 신호→검증→주문→체결 반영 (KIS mock) |
| 프론트 | Vitest + RTL | 모드 배너, 포지션/로그 테이블, 봇 토글 |

- KIS 실거래 API는 테스트에서 **항상 mock**. 실제 호출 금지.
- 절대규칙 3: 테스트 통과 없이 기능 완료 선언 금지.

---

## 운영 스크립트 (루트 배치)

| 스크립트 | 역할 |
|---------|------|
| `setup.bat` | 백엔드 venv + `pip install -e .[dev]`, 프론트 `npm install` (최초 1회) |
| `start.bat` | `scripts/start-server.ps1` 위임 — 백엔드(uvicorn :8000)+프론트(vite :5173)를 숨김 실행, `logs/`에 기록, **포트 감지**로 OK/FAIL 보고 |
| `stop.bat` | `scripts/stop-server.ps1` 위임 — **포트 + 저장소 폴더 기준**으로 종료(폴백 포트·고아 프로세스까지). `net session` 권한 경고 |
| `start_backend.bat` / `start_frontend.bat` | 개별 가시 창 실행(라이브 로그 확인용) |

설계 원칙(Reference `bat` 문서 기준):
- 배치/PS1 메시지는 **영문**(CMD CP949 깨짐 방지), PS1은 **ASCII**(PowerShell 5.1 BOM 이슈 방지).
- 종료는 포트만 보지 않고 **저장소 디렉터리에서 실행된 python/node**를 함께 정리 — Vite 폴백 포트(5174 등)와 자식 프로세스 누락 방지.
- Vite는 `strictPort: true`로 **5173 고정**(폴백으로 인한 종료 누락 원천 차단).
- 배치는 `%~dp0` 기반 자기 위치 인식(클론 경로 무관).
