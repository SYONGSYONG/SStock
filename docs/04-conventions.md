# 04-conventions.md — 개발 규칙

> 이 문서의 규칙은 전역 `CLAUDE.md` 절대규칙과 동일한 효력을 가진다.

---

## 1. 네이밍 컨벤션

### 백엔드 (Python)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일·모듈 | `snake_case.py` | `kis_client.py`, `strategy_engine.py` |
| 함수·변수 | `snake_case` | `get_current_price`, `daily_order_count` |
| 클래스 | `PascalCase` | `KisClient`, `MaCrossStrategy` |
| 상수 | `UPPER_SNAKE_CASE` | `DAILY_MAX_ORDERS`, `TR_ID_BUY` |
| Pydantic 모델 | `PascalCase` | `OrderRequest`, `PriceTick` |

### 프론트엔드 (React + TypeScript)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일 | `PascalCase.tsx` | `WatchList.tsx`, `PositionTable.tsx` |
| 훅 파일 | `use` 접두사 | `useLiveQuotes.ts`, `useBotStatus.ts` |
| 유틸 파일 | `kebab-case.ts` | `api-client.ts`, `format-price.ts` |
| props 타입 | 컴포넌트명 + `Props` | `WatchListProps` |
| Boolean | `is/has/can` 접두사 | `isBotRunning`, `hasPosition` |

### 공통

| 대상 | 규칙 |
|------|------|
| 환경 변수 | `UPPER_SNAKE_CASE` (`KIS_APP_KEY`) |
| API 경로 | `kebab-case` 복수 명사 (`/api/watchlist`, `/api/orders`) |
| DB 테이블/컬럼 | `snake_case` |

---

## 2. 폴더 구조

```
SStock/
├── docs/                      # 프로젝트 문서 (00~05)
├── Reference/                 # KIS API 명세 등 참고자료 (수정 금지)
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 진입점
│   │   ├── config.py          # 설정(pydantic-settings)
│   │   ├── kis/               # KIS API 클라이언트 (REST/WS/auth)
│   │   ├── bot/               # 봇 엔진 (asyncio 루프)
│   │   ├── strategies/        # 전략 (ma_cross, rsi …)
│   │   ├── services/          # 주문·포지션·안전가드 로직
│   │   ├── db/                # 스키마·마이그레이션·접근
│   │   ├── routers/           # API 라우터
│   │   └── schemas/           # Pydantic 모델
│   ├── tests/                 # pytest 테스트
│   ├── data/                  # SQLite 파일 (gitignore)
│   ├── .env                   # 시크릿 (gitignore)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/         # UI 컴포넌트
│   │   ├── hooks/              # 커스텀 훅
│   │   ├── api/                # 백엔드 호출
│   │   ├── lib/                # 유틸
│   │   └── types/             # 공용 타입
│   ├── __tests__/
│   └── package.json
├── .env.example
├── .gitignore
└── CLAUDE.md
```

> 폴더 구조 임의 변경 금지(절대규칙 5). 변경은 승인 후 진행.

---

## 3. Git 전략

### 브랜치

| 접두사 | 용도 | 예시 |
|--------|------|------|
| `feat/` | 새 기능 | `feat/ma-cross-strategy` |
| `fix/` | 버그 수정 | `fix/ws-reconnect` |
| `docs/` | 문서 | `docs/update-specs` |

### 커밋 메시지

```
<type>: <한국어 요약> (50자 이내)
```

타입: `feat` `fix` `docs` `test` `refactor` `chore`

예시:
```
feat: 이동평균 크로스 전략 신호 생성 구현
fix: 웹소켓 재연결 시 중복 구독 제거
test: 일일 주문 한도 초과 거부 케이스 추가
```

---

## 4. 코드 스타일

### Python

- 포매터/린터: **ruff** (format + lint). 타입체크: **mypy** (가능 범위).
- 타입 힌트를 모든 public 함수에 명시한다.
- `async`/`await`를 일관되게 사용 (블로킹 호출은 스레드풀로 격리).
- 예외를 삼키지 않는다. 도메인 에러는 명시적 예외 클래스 사용.
- 설정/외부 입력은 Pydantic으로 검증(시스템 경계 검증).

### TypeScript

- `any` 금지. 불명확 시 `unknown` + 타입 가드.
- 함수 반환 타입 명시. 객체는 `interface`, 유니온은 `type`.
- 서버 상태는 직접 fetch 훅으로, 실시간은 WebSocket 훅으로 관리.

### API 응답 형식

```
성공: { "data": <payload> }
실패: { "error": "<메시지>", "code": "<ERROR_CODE>" }
```

| HTTP | 용도 |
|------|------|
| 200 | 조회·수정 성공 |
| 201 | 생성 성공 |
| 400 | 요청 오류(검증 실패, 한도 초과 등) |
| 404 | 리소스 없음 |
| 409 | 상태 충돌(봇 정지 중 주문 등) |
| 500 | 서버 오류 |

---

## 5. 테스트 규칙

- 기능 구현과 테스트는 같은 커밋/PR에 포함. 테스트 없는 완료 선언 금지(절대규칙 3).
- KIS 실거래 API는 테스트에서 항상 mock. 실제 주문 호출 금지.
- 테스트 설명은 한국어. AAA(Arrange-Act-Assert) 구조.
- 백엔드 전략·안전가드는 단위 테스트 필수. 커버리지 목표 80%.

---

## 6. 보안 규칙

| 규칙 | 상세 |
|------|------|
| 시크릿 하드코딩 금지 | `KIS_APP_KEY`/`KIS_APP_SECRET`/token은 `os.environ`/설정으로만 |
| `.env` 커밋 금지 | `.gitignore`에 `.env`, `data/`, `*.db` 등록 PR 전 확인 |
| 로그 마스킹 | key/secret/token이 로그·에러·응답에 노출되지 않도록 마스킹 |
| 실전 가드 | `TRADING_MODE=live`는 환경변수 + 대시보드 확인 동시 충족 시에만 |
| 주문 한도 | 모든 주문 경로에서 일일 한도·종목 한도 검사 통과 필수 |
