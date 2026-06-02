# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에 지침을 제공한다.

## 현재 상태

이 프로젝트(**SStock**)는 **설계 문서 완료, 구현 착수 전** 상태다.

- **제품**: 한국투자증권(KIS) 국내주식 OpenAPI 기반 **실시간 시세 모니터링 + 룰 기반 자동 매매 봇**.
- **스택(확정)**: Python(FastAPI + asyncio) 백엔드 + React(Vite) 대시보드 + SQLite. 거래는 **모의투자 우선**.
- 상세는 `docs/00-overview.md`~`docs/05-tasks.md` 참조. 작업 전 이 6개 문서를 번호 순서대로 읽는다.
- 코드가 추가되면 `/init`을 다시 실행해 이 골격을 실제 아키텍처·명령어 참조로 보강한다.

## Reference (모든 작업 전에 읽을 것)

`Reference/doc/`에는 **형제 프로젝트**(*Framework5.0_Manager* — 읽기 전용 저장소/이슈/칸반
관리 대시보드)의 완성된 전체 doc 세트가 들어 있다. 이는 **SStock 자체의 명세가 아니라**,
이 프로젝트가 따라야 할 문서 구조·깊이·컨벤션의 **표준 예시**다.

| 파일 | 답하는 질문 |
| ---- | ---------- |
| `Reference/doc/00-overview.md`    | 왜 — 프로젝트 정의, 문서 매핑, 읽는 순서, 관심사 분리 근거 |
| `Reference/doc/01-product.md`     | 무엇 — 제품 목표, 페르소나, MVP 기능, 필드, 규칙 |
| `Reference/doc/02-specs.md`       | 어떻게 — 기술 스택, DB 스키마, API 설계, 환경 변수, 테스트 전략 |
| `Reference/doc/03-design.md`      | 어떻게 보이는가 — UI/UX 결정, 색상 토큰, 와이어프레임 |
| `Reference/doc/06-pages.md`       | 어디에 — URL 맵, 페이지별 컴포넌트, 데이터 흐름, 상태 |
| `Reference/doc/05-conventions.md` | 어떤 규칙 — 네이밍, 폴더 구조, Git 브랜치, 코드 스타일 |
| `Reference/doc/04-tasks.md`       | 무엇을 완료했나 — 단계별 검증이 포함된 Phase 체크리스트 |

**읽는 순서(건너뛰지 말 것):** `00 → 01 → 02 → 03 → 06 → 05 → 04`.
각 문서는 이전 문서가 형성한 맥락에 의존한다.

## 문서 주도 워크플로우 (필수)

이 저장소의 모든 작업은 **문서 우선(doc-first)**이다. 문서가 의도의 단일 진실 공급원이며,
코드는 문서를 따른다.

1. **모든 작업 시작 전** — SStock의 `docs/` 파일을 **번호 순서대로** 읽는다. 관련 문서를
   읽고 계획된 단계를 순서대로 따르기 전까지 코딩을 시작하지 않는다.
2. **작업 진행 중** — 구현 전·중에 대응하는 `docs/NN-*.md` 파일을 생성·갱신한다.
3. **문서 동기화** — 코드와 같은 변경에서 문서를 갱신한다. `05-tasks.md`에서는 검증 방법이
   실제로 통과한 후에만 단계를 완료(✅)로 표시한다.

### SStock `docs/` 레이아웃 (전역 6파일 표준)

```
docs/
├── 00-overview.md     # 왜 — 프로젝트 정의, 핵심 결정, 읽는 순서
├── 01-product.md      # 무엇 — 목표, 페르소나, MVP 기능, 안전 제약
├── 02-specs.md        # 어떻게 — 스택, KIS API 연동, DB 스키마, 환경 변수, 테스트
├── 03-design.md       # 어떻게 보이는가 — 대시보드 레이아웃, 색상, 실시간 흐름
├── 04-conventions.md  # 어떤 규칙 — 네이밍, 폴더 구조, Git, 코드 스타일, 보안
└── 05-tasks.md        # 무엇을 완료했나 — Phase별 작업 순서 + 완료 여부 + 검증
```

- 6개 문서 모두 작성 완료(Phase 0). 읽는 순서: `00 → 01 → 02 → 03 → 04 → 05`.
- 관심사당 하나의 문서, 코드와 문서를 같은 커밋에서 동기화한다.
- `Reference/`는 형제 프로젝트 문서 예시 + KIS API 명세(`Reference/API_DOC/`) 보관소다(수정 금지).

### 문서 언어 (필수)

**모든 문서는 한글(한국어)로 작성한다.** 기술 용어, 코드 식별자, 파일 경로, 명령어,
외부 고유명사는 원형을 유지하고, 그 외 서술은 한글로 작성한다.

## Reference에서 상속하는 컨벤션

SStock이 자체 `05-conventions.md`를 작성하기 전까지는 Reference의 컨벤션을 기본값으로
따른다(`Reference/doc/05-conventions.md` 참고). 주요 항목:

- **API 응답 형식** — 성공 `{ "data": <payload> }`, 실패 `{ "error": "<메시지>", "code": "<CODE>" }`.
- **네이밍** — 백엔드 파일 `kebab-case`, React 컴포넌트 `PascalCase.tsx`, 훅 `use*`,
  DB 테이블/컬럼 `snake_case`, 상수 `UPPER_SNAKE_CASE`, 불리언 `is/has/can` 접두사.
- **테스트는 기능과 함께** — 테스트 통과 없이는 "완료" 없음. 백엔드 테스트는 인메모리
  SQLite 사용, 테스트 설명은 한국어로 작성.
- **Git 커밋** — `<type>: <한국어 요약>` (`feat`/`fix`/`docs`/`test`/`refactor`/`chore`).
- **보안** — 시크릿은 `process.env`로만 참조. `.env`나 DB 파일은 커밋 금지.

> 이는 상속된 기본값이며 SStock의 확정 스택이 아니다. 실제 스택은 사용자와 확인한 뒤
> `doc/02-specs.md`에 기록하고 나서 적용한다.

## 환경 참고

- 플랫폼: Windows 11, PowerShell 기본 셸 (PowerShell 문법 사용; Bash는 Bash 도구로 사용 가능).
- 아직 git 저장소가 아님 — 첫 커밋 전에 `git init` 실행.

## 첫 기능 추가 전에

전역 워크플로우에 따라 **연구 및 재사용(Research & Reuse)**을 먼저 수행한다. Reference
프로젝트는 React 19 + Vite + Express + better-sqlite3 스택으로 저장소/이슈/칸반 관리를
이미 해결하고 있으므로, SStock에 맞는 부분은 그 검증된 구조를 채택·이식하는 것을 고려한다.
기술 스택과 제품 범위를 사용자와 확정하고 `doc/00`~`doc/02`에 기록한 뒤, 그 문서를 기준으로
구현한다.
