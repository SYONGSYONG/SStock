# 02-specs.md — 기술 명세

## 기술 스택 (확정)

| 레이어 | 기술 | 버전 기준 | 비고 |
|--------|------|----------|------|
| 프론트엔드 | React + TypeScript | React 19, TS 5 | Vite 8 번들러 |
| UI 컴포넌트 | shadcn/ui + Tailwind CSS | Tailwind 3 | |
| 백엔드 | Node.js + Express | Node 20 LTS, Express 4 | TypeScript |
| 보안 미들웨어 | helmet + express-rate-limit | helmet 8, express-rate-limit 8 | 보안 헤더 + 로그인 무차별 대입 방어 |
| 데이터베이스 | SQLite (better-sqlite3) | 최신 안정버전 | 파일 기반, 별도 서버 불필요 |
| 인증 | JWT (jsonwebtoken) | | 시크릿은 환경 변수 |
| GitHub API | Octokit REST | | 읽기 전용 스코프 |
| 테스트 (백엔드) | Vitest + Supertest | | |
| 테스트 (프론트엔드) | Vitest + React Testing Library | | |
| 데스크톱 앱 | Electron | 35 | electron 브랜치 전용 |

> **WinForm 비유**: SQLite = 앱과 함께 배포되는 LocalDB. 별도 SQL Server 설치 없이 `.db` 파일 하나로 동작한다.

---

## 비기능 요구사항 명세

| 항목 | 요구사항 | 구현 방법 |
|------|---------|----------|
| 동시 접속 | 최소 10명 동시 접속 지원 | Express 기본 스레드 + SQLite WAL 모드 활성화 |
| 상태 전환 로그 | 모든 칸반 상태 전환을 DB에 기록 | `transition_logs` 테이블에 INSERT (삭제·수정 불가) |
| 테스트 | 모든 기능은 작성된 테스트를 통과해야 함 | 백엔드 API 통합 테스트 + 프론트엔드 컴포넌트 단위 테스트 |
| 네트워크 접근 | 동일 네트워크 내 다른 PC에서 접속 가능 | Express 서버 `0.0.0.0` 바인딩, 방화벽 포트 허용 |

---

## 데이터베이스 스키마

> **레거시 정리**: 초기 버전의 `admin_settings` 테이블(관리자 비밀번호 단일 행)은
> Phase 5에서 members 기반 인증으로 전환된 후 사용되지 않아 마이그레이션 v7에서 제거됐다.
> 관리자 인증은 `members` 테이블의 `role='admin'` 계정 + JWT로 일원화되어 있다.

### members (회원)

```sql
CREATE TABLE members (
  id                       INTEGER PRIMARY KEY AUTOINCREMENT,
  name                     TEXT    NOT NULL,
  affiliation              TEXT,                -- 소속
  position                 TEXT,                -- 직급
  phone                    TEXT,                -- 전화번호
  email                    TEXT UNIQUE,         -- 로그인 ID
  password_hash            TEXT,                -- bcrypt 해시
  role                     TEXT NOT NULL DEFAULT 'member'
                             CHECK(role IN ('member','team_member','admin')),
  is_active                INTEGER NOT NULL DEFAULT 1,   -- 컬럼 default는 1, 회원가입 INSERT 시 0 명시
  password_reset_requested INTEGER NOT NULL DEFAULT 0,
  password_change_required INTEGER NOT NULL DEFAULT 0,  -- 1이면 다음 로그인 시 /force-change-password로 강제 라우팅
  rejected_at              TEXT,                -- 거절 시각 (NULL이면 거절 아님). is_active=0과 함께 사용
  created_at               TEXT NOT NULL DEFAULT (datetime('now'))
);
-- 신규 컬럼은 ALTER TABLE ... ADD COLUMN 마이그레이션으로 추가 (schema_migrations로 추적)
-- 초기 MASTER 계정: role='admin', email='master@admin.local', password=bcrypt('1234'), is_active=1,
--                  password_change_required=1 (첫 로그인 시 강제 변경)
-- 회원가입(register): is_active=0 으로 INSERT (관리자 승인 대기) → admin이 승인 시 1로 전환
-- 거절(reject): is_active=0 유지 + rejected_at = NOW. 본인이 가입 취소(cancel-registration)할 때까지 행은 유지된다.
-- 거절 후 admin이 다시 승인(approve)하면 rejected_at = NULL + is_active = 1로 복구된다.
-- 비밀번호 변경 성공 시 password_change_required = 0, admin이 reset-password 호출 시 1로 set.
```

### issues (이슈 / To Do)

```sql
CREATE TABLE issues (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  title          TEXT    NOT NULL,
  content        TEXT    NOT NULL,
  requester_name TEXT    NOT NULL,               -- 의뢰자 표시명 (로그인 사용자 name 자동 설정)
  requester_id   INTEGER REFERENCES members(id), -- 소유자 (삭제 권한 확인용)
  registered_at  TEXT    NOT NULL DEFAULT (datetime('now')),
  assignee_id    INTEGER REFERENCES members(id),
  completed_at   TEXT,
  difficulty     TEXT CHECK(difficulty IN ('LOW','MEDIUM','HIGH')),
  is_closed      INTEGER NOT NULL DEFAULT 0,
  type           TEXT    NOT NULL DEFAULT 'issue' CHECK(type IN ('issue','todo'))
);
-- 신규 컬럼 마이그레이션: ALTER TABLE issues ADD COLUMN requester_id ...
```

### issue_kanban (이슈 ↔ 칸반 다대다)

```sql
CREATE TABLE issue_kanban (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id   INTEGER NOT NULL REFERENCES issues(id),
  repo_key   TEXT    NOT NULL,   -- 예: "SYSTEM3-SW/Framework5.0"
  status     TEXT    NOT NULL CHECK(status IN ('TO DO','DOING','DONE','PENDING')),
  updated_at TEXT    NOT NULL DEFAULT (datetime('now')),
  UNIQUE(issue_id, repo_key)
);
```

### comments (댓글)

```sql
CREATE TABLE comments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id   INTEGER NOT NULL REFERENCES issues(id),
  author_id  INTEGER REFERENCES members(id),  -- NULL이면 시스템 댓글
  content    TEXT    NOT NULL,
  is_system  INTEGER NOT NULL DEFAULT 0,      -- 1 = 자동 댓글
  created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### transition_logs (상태 전환 로그 — 불변)

```sql
CREATE TABLE transition_logs (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  issue_id       INTEGER NOT NULL REFERENCES issues(id),
  repo_key       TEXT    NOT NULL,
  from_status    TEXT    NOT NULL,
  to_status      TEXT    NOT NULL,
  actor_id       INTEGER REFERENCES members(id),
  transitioned_at TEXT   NOT NULL DEFAULT (datetime('now'))
);
-- 이 테이블에는 UPDATE, DELETE를 수행하지 않는다.
```

### schema_migrations (마이그레이션 이력 — 자동)

```sql
CREATE TABLE schema_migrations (
  version    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- backend/src/db/index.ts의 MIGRATIONS 배열을 기준으로 부팅 시 자동 적용.
-- 한 번 적용된 version은 다음 부팅 시 건너뛴다. 각 up()은 try/catch로 idempotent하게 작성.
-- 운영 DB 업그레이드는 코드 배포만으로 자동 진행됨. CLAUDE.md 9번 규칙(스키마 변경 마이그레이션 포함)을 보장.
```

### 인덱스 (조회 핫 컬럼)

마이그레이션 v6에서 일괄 생성. `CREATE INDEX IF NOT EXISTS`라 옛 DB에도 안전.

```sql
CREATE INDEX idx_issue_kanban_issue    ON issue_kanban(issue_id);
CREATE INDEX idx_issue_kanban_repo     ON issue_kanban(repo_key);
CREATE INDEX idx_comments_issue        ON comments(issue_id);
CREATE INDEX idx_transition_logs_issue ON transition_logs(issue_id);
CREATE INDEX idx_members_email         ON members(email);
CREATE INDEX idx_issues_type_closed    ON issues(type, is_closed);
```

---

## 허용된 상태 전환 매트릭스

코드에서 이 표를 단일 진실 공급원(Single Source of Truth)으로 사용한다.

```typescript
// backend/src/constants/kanban.ts
export const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  'TO DO':  ['DOING',   'PENDING'],
  DOING:    ['DONE',    'PENDING'],
  DONE:     ['DOING',   'PENDING'],
  PENDING:  ['TO DO',   'DOING',  'DONE'],
};
```

---

## API 설계

### 레포지토리

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/repos` | 슈퍼 레포 + 서브모듈 목록 |
| GET | `/api/repos/:org/:repo/commits` | 커밋 히스토리 (최신 30건) |
| GET | `/api/repos/:org/:repo/commits/:sha` | 커밋 상세 (변경 파일, 통계) |
| GET | `/api/repos/:org/:repo/readme` | README.md 내용 (base64 디코딩, 5분 캐시) |
| GET | `/api/repos/:org/:repo/clone-url` | 토큰 포함 HTTPS clone URL 반환 (Electron main process 전용). **admin 전용** (GITHUB_TOKEN 평문 노출 방지) |

> **클론 정책**: 웹 브라우저에서는 서버에 직접 클론하지 않고 `git clone <url>` **명령어 복사**만 제공한다(사용자가 본인 PC 터미널에서 실행). 로컬 클론은 Electron 데스크톱 앱에서만 수행하며, main process가 `clone-url`(admin 전용)로 토큰 포함 URL을 받아 사용자 PC에 클론한다. 과거의 `POST /api/repos/:org/:repo/clone`(서버 측 git clone)은 무의미·공격면 우려로 제거됐다. 그 외 레포 조회 엔드포인트는 인증 없이 접근 가능(읽기 전용 GitHub 데이터).

### 인증 (Auth)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/auth/login` | 이메일+비밀번호 → JWT 반환. `rejected_at IS NOT NULL` 시 403 `REGISTRATION_REJECTED` (`is_active=0`보다 우선 체크). `is_active=0` 시 403 `PENDING_APPROVAL`. **rate limit: 같은 IP 1분당 10회 초과 시 429 `RATE_LIMITED`** (테스트 환경 제외) |
| POST | `/api/auth/logout` | 로그아웃 (JWT 필요, 활동 로그 기록) |
| POST | `/api/auth/register` | 회원가입 (name, affiliation, position, phone, email, password). `is_active=0`으로 생성됨. 비밀번호 정책 위반 시 400 `INVALID_FIELD` |
| GET | `/api/auth/me` | 내 정보 조회 (JWT 필요) |
| PATCH | `/api/auth/password` | 비밀번호 변경 (JWT 필요). 새 비밀번호가 정책 위반 시 400 `INVALID_FIELD` |
| POST | `/api/auth/reset-request` | 비밀번호 초기화 요청 (이메일 입력) |
| POST | `/api/auth/cancel-registration` | 거절된 본인 회원가입 취소 (이메일+비밀번호 재확인 후 자체 삭제). `rejected_at IS NULL`이면 400 `NOT_REJECTED` |

### 회원

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/members` | 전체 회원 목록 (JWT 필요) |
| GET | `/api/members/team` | 팀원 목록 (team_member + admin, 칸반 담당자 선택용) |
| GET | `/api/members/:id` | 회원 상세 |
| PATCH | `/api/members/:id` | 프로필 수정 (본인 또는 admin) |
| PATCH | `/api/members/:id/role` | 역할 변경 (admin 전용). admin 강등 시 활성 admin 수 ≤ 1이면 409 `LAST_ADMIN` |
| POST | `/api/members/:id/approve` | 회원가입 승인 (`is_active=1`, `rejected_at=NULL`로 복구. admin 전용). 이미 활성 시 400 `ALREADY_ACTIVE` |
| POST | `/api/members/:id/reject` | 회원가입 거절 (admin 전용). 삭제 대신 `rejected_at=NOW` 기록 → 본인이 cancel-registration 호출할 때까지 행 유지. 이미 활성/거절 시 400 |
| POST | `/api/members/:id/reset-password` | 비밀번호 1234 초기화 (admin 전용) |
| DELETE | `/api/members/:id/reset-request` | 비밀번호 초기화 요청 거절 (admin 전용) |
| DELETE | `/api/members/:id` | 회원 삭제 (admin 전용). 활성 admin 삭제 시 활성 admin 수 ≤ 1이면 409 `LAST_ADMIN` |

### 이슈

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/issues` | 목록 (쿼리: `repoKey`, `status`, `type`) — 전체 통합 |
| POST | `/api/issues` | 등록 (body: `title`, `content`, `requester_name`, `type`) |
| GET | `/api/issues/:id` | 상세 (assignee_name JOIN 포함) |
| PATCH | `/api/issues/:id` | 수정 (제목, 본문, 담당자, 완료일, 난이도). 제목/본문 공백만 입력 시 400 `INVALID_FIELD` |
| DELETE | `/api/issues/:id` | 삭제 (댓글·칸반·로그 연쇄 삭제) |
| POST | `/api/issues/:id/close` | 종결 (is_closed=1, 칸반 전체 제거) |
| POST | `/api/issues/:id/revive` | 되살리기 (is_closed=0, 칸반 미복원) |

### 댓글

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/issues/:id/comments` | 댓글 목록 (author_name JOIN 포함) |
| POST | `/api/issues/:id/comments` | 댓글 등록 (JWT 필요, author_id 자동 설정) |
| PATCH | `/api/issues/:id/comments/:commentId` | 댓글 수정 (본인 또는 admin). `is_system=1` 시 403, 빈 내용 400 |
| DELETE | `/api/issues/:id/comments/:commentId` | 댓글 삭제 (본인 또는 admin). `is_system=1` 시 403 |

### 칸반

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/kanban/:org/:repo` | 특정 레포 칸반 조회. `?unified=true` 시 전체 통합 |
| POST | `/api/kanban` | 이슈를 레포 칸반에 등록 (TO DO, 복수 레포 개별 요청) |
| DELETE | `/api/kanban/:issueId/:org/:repo` | 칸반 등록 해제 |
| PATCH | `/api/kanban/:issueId/:org/:repo/status` | 상태 전환 (동기화 + 로그 + 자동 댓글) |

### 로그

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/logs/:issueId` | 특정 이슈의 전환 로그 조회 |
| GET | `/api/admin/activity-log?lines=N` | 활동 로그 텍스트 파일 마지막 N줄 조회 (admin 전용, 기본 500줄, 최대 2000줄) |

### 백업 / 복원

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/admin/backup` | DB(`app.db`) + `.env` + `meta.json`을 zip으로 묶어 다운로드 (admin 전용). 응답: `application/zip`, 파일명 `framework5_backup_YYYY-MM-DDTHH-MM-SS.zip`. 호출 시 WAL 체크포인트 자동 수행 |
| POST | `/api/admin/restore` | 백업 zip 업로드(multipart, field name=`file`, 최대 100MB)로 DB와 `.env`를 덮어씀 (admin 전용). zip slip 방지: 허용된 항목(`app.db`, `.env`, `meta.json`)만 허용, `..`/경로 분리자 금지. 기존 파일은 `.bak.<timestamp>`로 보존되며 실패 시 자동 롤백. **DB 복원 성공 시 응답 직후 프로세스 종료** → 운영자가 재시작해야 새 DB로 가동됨. `meta.schemaVersion` 불일치 시 400 `INVALID_BACKUP` |

### 버전

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/version` | 서버 버전 정보 반환 (인증 불필요). 응답: `{ version, gitSha, startTime, host, origin }` — version은 `backend/package.json`의 version, gitSha는 모듈 로드 시점의 `git rev-parse --short HEAD`, startTime은 서버 기동 ISO 시각, host/origin은 요청을 받은 실제 host:port와 `proto://host:port`(Vite proxy 환경에서도 정확). 클라이언트는 마운트 시 + 5분마다 호출하여 메이저 버전 불일치 시 상단 경고 배너 표시, Electron 로그인 화면 풋터에서 origin을 "현재서버" 줄로 표시 |

### 활동 로그 파일

| 항목 | 값 |
|------|-----|
| 경로 | `LOG_DIR/activity.log` (기본 `backend/logs/activity.log`) |
| 형식 | `[YYYY-MM-DD HH:MM:SS] [CATEGORY] 사용자(역할) 동작 — 상세` |
| 카테고리 | `LOGIN`, `LOGOUT`, `ISSUE`, `COMMENT`, `KANBAN`, `MEMBER` (백업/복원도 MEMBER로 통합) |
| 기록 이벤트 | 로그인 성공·실패, 로그아웃, 회원가입, 비밀번호 변경·초기화 요청, 프로필 수정, 회원 승인·거절·역할 변경·삭제, 회원가입 본인 취소, 이슈/To Do 등록·수정·종결·되살리기·삭제 (수정 시 변경 필드를 detail에 기록), 댓글 추가·수정·삭제, 칸반 등록·해제·상태 변경, 백업 다운로드, 복원 실행 |
| 로테이션 | 파일 크기 10MB 초과 시 `activity.YYYY-MM-DD_HHMMSS.log`로 자동 rename, 새 파일로 이어서 기록 |

---

## 환경 변수 목록

```env
# .env.example

# 실행 환경 — 'production'일 때 부팅 시 JWT_SECRET 가드가 활성화된다.
NODE_ENV=development

# GitHub
GITHUB_TOKEN=           # Personal Access Token (read:org, repo 읽기 전용)
GITHUB_ORG=SYSTEM3-SW
GITHUB_SUPER_REPO=Framework5.0

# 서버
PORT=3000
HOST=0.0.0.0            # 네트워크 내 타 PC 접속 허용

# 보안
# - development: 미설정 시 'dev-secret' 폴백 (테스트 호환)
# - production: 미설정/32자 미만/'dev|change|example|sample|test|default|secret-here' 패턴 포함 시 부팅 차단
JWT_SECRET=

# 데이터베이스
DATABASE_PATH=./data/app.db

# CORS — 콤마 구분 화이트리스트. 미설정 시 localhost dev 기본값(localhost:5173, 127.0.0.1:5173)만 허용.
# '*' 단독 입력 시 모두 허용 (운영 권장 안 함). origin 없는 요청(curl, Electron, server-to-server)은 항상 통과.
CORS_ORIGIN=http://localhost:5173

# 로그
LOG_DIR=./logs          # 활동 로그 저장 경로 (기본: backend/logs/)
```

---

## 테스트 전략

### 백엔드 — API 통합 테스트 (Vitest + Supertest)

테스트 실행 전 인메모리 SQLite를 사용하여 실 DB와 격리한다.

**테스트 파일 위치**: `backend/src/__tests__/`

#### 필수 테스트 목록

| 파일 | 테스트 대상 | 핵심 케이스 |
|------|------------|-----------|
| `members.test.ts` | 회원/팀원 | `/api/auth/register` 가입, 인증 토큰 검사, 목록·삭제 권한, **비밀번호 정책 위반(짧음/숫자없음/영문없음/특수문자/공백) 400**, **활동 이력 있는 회원 삭제 시 참조 NULL 익명화** |
| `issues.test.ts` | 이슈 CRUD | 인증 가드(401), 등록·상세·삭제, 제목/본문/난이도 수정, 빈 입력 400 |
| `comments.test.ts` | 댓글 | 등록/목록, 수정(작성자·admin만), `is_system` 보호, 권한 위반 403, 빈 내용 400 |
| `kanban.test.ts` | 칸반 상태 전환 | 허용 전환 성공, 금지 전환 시 400, 복수 동기화, 인증 가드, **미등록 칸반 해제 404** |
| `transition.test.ts` | 전환 로그 | 전환 시 로그·자동 댓글 생성, 로그 불변성 |
| `backup.test.ts` | 백업/복원 | 백업→복원 라운드트립, SHA256 변조 거부, zip slip 방어, 스키마 mismatch, .bak 자동 정리 |

전체 백엔드 테스트는 **69개 모두 통과**가 baseline이다. PR 머지 전에 `npm run test`로 확인.

> 테스트는 토큰을 `__tests__/test-helpers.ts`의 `masterAdmin(db)` / `seedMember(db, name, role)` / `tokenFor(user)`로 발급한다. JWT_SECRET을 직접 import하지 말 것 (helpers가 `process.env.JWT_SECRET`을 unset해 `dev-secret`을 보장).

#### 상태 전환 테스트 핵심 케이스

```typescript
// 허용 전환: 성공해야 함
describe('허용된 상태 전환', () => {
  test.each([
    ['TODO',    'DOING'],
    ['DOING',   'DONE'],
    ['DONE',    'DOING'],
    ['TODO',    'PENDING'],
    ['DOING',   'PENDING'],
    ['DONE',    'PENDING'],
    ['PENDING', 'TODO'],
    ['PENDING', 'DOING'],
    ['PENDING', 'DONE'],
  ])('%s → %s 전환 성공', async (from, to) => { ... });
});

// 금지 전환: 400 반환해야 함
describe('금지된 상태 전환', () => {
  test.each([
    ['TODO',  'DONE'],
    ['DONE',  'TODO'],
    ['DOING', 'TODO'],
  ])('%s → %s 전환 시 400 반환', async (from, to) => { ... });
});

// 동기화: repo-A에서 전환 시 repo-B도 변경되어야 함
test('복수 칸반 동기화', async () => { ... });

// 로그: 전환 시 transition_logs에 레코드 생성
test('상태 전환 시 로그 자동 생성', async () => { ... });

// 자동 댓글: 전환 시 comments에 is_system=1 레코드 생성
test('상태 전환 시 자동 댓글 생성', async () => { ... });
```

### 프론트엔드 — 컴포넌트 단위 테스트 (Vitest + RTL)

**테스트 파일 위치**: `frontend/src/__tests__/`

| 파일 | 테스트 대상 | 핵심 케이스 |
|------|------------|-----------|
| `KanbanBoard.test.tsx` | 칸반 보드 렌더링 | 컬럼 4개 표시, 카드 렌더링, 레포 태그 표시 |
| `IssueForm.test.tsx` | 이슈 등록 폼 | 필수 필드 미입력 시 submit 불가, 정상 제출 |
| `StatusBadge.test.tsx` | 상태 뱃지 | 각 상태별 올바른 텍스트·색상 렌더링 |
| `TransitionButton.test.tsx` | 상태 전환 버튼 | 허용 전환만 버튼 노출, 금지 전환 버튼 미노출 |
| `client.test.ts` | API 클라이언트 | `api()` 성공/실패, 토큰 유무별 Authorization 헤더, `ApiError` status·code 보존, `readAuthToken` 우선순위 |
| `AuthContext.test.tsx` | 인증 상태 | login persist 분기(local/session), logout 정리, role별 isAdmin/isTeamMember, markPasswordChanged, 토큰 복원 |

전체 프론트엔드 테스트는 **40개 모두 통과**가 baseline이다.

---

## GitHub API 사용 원칙

- 토큰 스코프: `read:org`, `repo` (읽기 전용)
- 모든 GitHub API 호출은 **백엔드에서만** 수행 (프론트에서 토큰 직접 사용 금지)
- Rate Limit 대응: 레포 목록·서브모듈 목록은 **5분 캐시** 적용
- 커밋 히스토리: 최신 30건만 조회

---

## SQLite WAL 모드 설정

동시 접속 10명 이상을 위해 앱 시작 시 WAL(Write-Ahead Logging) 모드를 활성화한다.

```typescript
// backend/src/db/index.ts
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
```

> **WinForm 비유**: WAL 모드 = DataGridView에서 여러 스레드가 동시에 읽을 수 있도록 읽기 잠금을 분리하는 것과 유사하다.

---

## 운영 보호 (production 가드)

| 항목 | 동작 | 위치 |
|------|------|------|
| 보안 헤더 (helmet) | HSTS·X-Content-Type-Options·X-Frame-Options 등 표준 헤더 적용. CSP는 비활성(JSON API 서버), CORP는 cross-origin(프론트·Electron 응답 허용) | `backend/src/app.ts` |
| 로그인 rate limit | `POST /api/auth/login` 같은 IP 1분당 10회 초과 시 429 `RATE_LIMITED`. 테스트 환경(`NODE_ENV=test`)에서는 비활성 | `backend/src/routes/auth-router.ts` |
| 비밀번호 정책 | 8자 이상 + 영문자(대소문자 무관) 1자 이상 + 숫자 1자 이상, 특수문자·공백 불가. register·changePassword에서 검증, 위반 시 400 `INVALID_FIELD` | `backend/src/services/auth-service.ts` (`validatePassword`), `frontend/src/lib/password.ts` |
| JWT_SECRET 검증 | `NODE_ENV=production`에서 미설정·32자 미만·기본 패턴(`dev|change|example|sample|test|default|secret-here`) 포함 시 부팅 차단. 런타임 조회는 `config.getJwtSecret()`로 일원화 | `backend/src/config.ts` |
| CORS 화이트리스트 | `CORS_ORIGIN` 콤마 구분 목록만 허용. 미설정 시 `localhost:5173` 기본값. origin 없는 요청은 통과 | `backend/src/app.ts` |
| 초기 비밀번호 강제 변경 | master 자동 생성 + admin이 비밀번호 초기화한 계정은 `password_change_required=1` → 로그인 후 `/force-change-password` 강제 라우팅. 변경 성공 시 0으로 reset | `auth-service.ts`, `frontend/.../ForceChangePasswordPage.tsx` |
| 에러 응답 정보 최소화 | 비-`AppError`는 production에서 스택 전체를 stdout에 남기지 않고 메시지만 기록(내부 경로·SQL 노출 방지), dev는 전체 출력 | `backend/src/middlewares/error.ts` |
| Graceful shutdown | `SIGTERM/SIGINT` 수신 시 `server.close → wal_checkpoint(TRUNCATE) → db.close → exit`. 10초 안에 안 끝나면 강제 종료 | `backend/src/index.ts` |
| 치명적 예외 처리 | `uncaughtException` / `unhandledRejection`도 graceful path로 종료(exit 1) | `backend/src/index.ts` |
| 스키마 마이그레이션 추적 | `schema_migrations` 테이블 + 부팅 시 자동 적용. 한 번 적용된 version은 재실행 안 됨. v7에서 레거시 `admin_settings` 테이블 제거 | `backend/src/db/index.ts` |

---

## 최초 설치 절차 (git clone 직후)

> **중요**: 이 프로젝트는 **모노레포 구조**(루트 + `backend/` + `frontend/` 두 개의 독립 패키지)다.
> 루트 폴더에는 `package.json`이 **없으며**, 의존성은 두 하위 폴더에서 **각각 수동 설치**해야 한다.

### 사전 준비

| 항목 | 요구 사항 | 확인 명령 |
|------|----------|----------|
| Node.js | 20 LTS 이상 | `node -v` |
| npm | 10 이상 (Node.js 동봉) | `npm -v` |

Node.js 미설치 시 https://nodejs.org 에서 LTS 버전 설치.

### 설치 단계

```powershell
# 1. 레포 클론
git clone https://github.com/SYSTEM3-SW/Framework5.0_Manager.git
cd Framework5.0_Manager

# 2. 백엔드 의존성 설치 (필수, 수동)
cd backend
npm install
cd ..

# 3. 프론트엔드 의존성 설치 (필수, 수동)
cd frontend
npm install
cd ..

# 4. 백엔드 환경 변수 설정 (필수 — GitHub 연동 사용 시)
#    backend/.env.example 을 참고하여 backend/.env 작성
#    GITHUB_TOKEN, GITHUB_ORG, GITHUB_SUPER_REPO가 없으면 레포지토리 페이지가
#    무한 로딩 상태에 빠진다. .env는 git에 포함되지 않으므로 새 PC마다 수동 작성 필요
#    → 기존 운영 서버에서 가져오려면 관리자 페이지의 "백업 다운로드"를 사용

# 5. 실행
.\start_server.bat
```

### 자주 발생하는 오류

| 오류 메시지 | 원인 | 해결 |
|------------|------|------|
| `ENOENT: ... \Framework5.0_Manager\package.json` | 루트에서 `npm install` 실행 | 루트 대신 `backend`, `frontend` 각각에서 실행 |
| `'tsx' is not recognized ...` | `backend/node_modules` 없음 | `cd backend; npm install` |
| `'vite' is not recognized ...` | `frontend/node_modules` 없음 | `cd frontend; npm install` |
| `[ERROR] Backend package.json not found` | `start_server.bat`의 BASE 경로가 실제 클론 위치와 불일치 | `start_server.bat`은 `%~dp0` 기반으로 자기 위치를 자동 인식 — 최신 버전 사용 확인 |
| `npm.cmd not found` | Node.js 미설치 또는 PATH 미등록 | Node.js 재설치 후 새 터미널 |
| 레포지토리 페이지가 무한 로딩 (스피너만 회전) | `backend/.env`에 `GITHUB_TOKEN`/`GITHUB_ORG`/`GITHUB_SUPER_REPO` 미설정 | `backend/.env`에 위 3개 변수 작성 후 백엔드 재시작. 기존 서버에서 옮길 땐 관리자 페이지 "백업 다운로드" → 새 PC에서 "복원 실행" |

### 왜 루트에서 한 번에 설치되지 않는가

워크스페이스(`npm workspaces`) 또는 모노레포 빌드 도구(`turbo`, `nx` 등)를 도입하지 않은 단순 분리 구조이기 때문이다.
프론트엔드와 백엔드는 빌드·실행·테스트가 완전히 독립적이며, 각자의 `node_modules`를 가진다.
향후 워크스페이스 통합이 필요해지면 별도 논의 후 도입한다.

> **WinForm 비유**: 솔루션(`.sln`) 하나에 두 개의 `.csproj`가 있는데, NuGet restore는 솔루션 루트가 아닌 각 프로젝트 폴더에서 따로 실행하는 상황과 같다.

---

## 데이터 백업 / 복원

서버 이전, 디스크 장애, 운영 PC 교체 상황에 대비해 admin 사용자가 데이터를 zip 하나로 묶어 가져갈 수 있다.

### 백업 파일 구성

```
framework5_backup_YYYY-MM-DDTHH-MM-SS.zip
├── app.db        ← SQLite DB 전체 (회원, 이슈, 칸반, 댓글, 전환 로그)
├── .env          ← 환경 변수 (GITHUB_TOKEN, JWT_SECRET 등 시크릿 포함)
└── meta.json     ← 백업 시점 메타데이터 (createdAt, schemaVersion, appVersion)
```

### 운영 흐름

1. **백업 생성**: 관리자 페이지 → "데이터 백업 / 복원" → `백업 다운로드 (zip)` 버튼
   - 호출 시 SQLite WAL checkpoint를 자동 수행해 일관된 스냅샷 보장
   - 활동 로그에 다운로드 기록 (`MEMBER` 카테고리)
2. **백업 파일 보관**: zip 안의 `.env`에 시크릿이 들어 있으므로 **암호화된 저장소나 사내 보안 채널로 이관**
3. **복원**: 새 서버에 같은 절차로 초기 설치(`npm install` 등) 완료 후 관리자 로그인 → `복원 실행`으로 zip 업로드
   - DB 복원에 성공하면 백엔드 프로세스가 자동 종료됨 (살아있는 SQLite의 파일 핸들 교체 불가) → `start_server.bat` 등으로 **재기동 필요**

### 안전 장치

| 위협 | 방어 |
|------|------|
| zip slip (악성 백업이 임의 경로에 파일 작성) | 항목 이름 화이트리스트(`app.db`, `.env`, `meta.json`)만 허용, `..`/경로 분리자 포함 시 400 거부 |
| 호환되지 않는 백업 (다른 스키마 버전) | `meta.schemaVersion`이 서버 상수와 다르면 400 거부 |
| 백업 파일 손상·변조 | `meta.hashes`에 `app.db`/`.env`의 SHA256을 박고 복원 직전 검증. 옛 백업(`hashes` 없음)은 통과 — 하위 호환 |
| 백업 도중 동시 쓰기로 인한 일관성 깨짐 | `createBackup` 진입 시 `BEGIN IMMEDIATE; COMMIT;`으로 진행 중 쓰기 종료를 보장 후 WAL checkpoint |
| 복원 도중 실패로 인한 데이터 손실 | 기존 파일을 `*.bak.<timestamp>`로 이동 후 새 파일 쓰기, 실패 시 자동 롤백. 롤백 자체가 실패한 항목은 에러 메시지에 상세 포함 |
| 살아있는 DB 위에 덮어쓰기 (Windows 파일 잠금) | 복원 직전 `db.close()`로 핸들 해제 → 파일 교체 → 응답 후 `process.exit(0)`으로 외부 재기동 유도 |
| EBUSY / EPERM 잠금 (stop_server 직후 잠시 남는 핸들) | `safeMove`에 200ms × 25회(최대 5초) retry, WAL/SHM 사이드카는 rename 실패 시 unlink로 약화 처리 |
| `.bak.<timestamp>` 누적 | 백업·복원 시점에 7일 이상 된 `.bak`을 자동 정리 (`BAK_RETENTION_DAYS = 7`) |
| 권한 우회 (웹 UI) | 두 엔드포인트 모두 `requireAdmin` 미들웨어로 admin role만 허용 |
| 권한 우회 (CLI/배치) | `restore_server.bat`, `rollback_server.bat`은 `net session`으로 관리자 권한 확인 후 진행. 부족 시 abort |
| 거대 파일 업로드 (DoS) | `multer` 메모리 저장소 + 100MB 상한 |
| CLI를 살아있는 서버 위에 실행 | `restore-from-file.ts`가 부팅 시 port 3000 listening 여부를 확인 → 살아있으면 exit 2 |

### 의존 패키지

| 패키지 | 용도 |
|--------|------|
| `adm-zip` | zip 읽기/쓰기 (단일 패키지, 외부 의존성 없음) |
| `multer` | Express multipart/form-data 업로드 |
| `@types/adm-zip`, `@types/multer` | TypeScript 타입 정의 (devDependencies) |

### 운영 도구 (배치 / 스크립트)

| 도구 | 목적 | 관리자 권한 |
|------|------|--------|
| `start_server.bat` | 백엔드 + 프론트 dev 서버 기동 | 권장 |
| `stop_server.bat` | port 3000/5173 listening 프로세스 + Framework5.0_Manager 디렉터리 내 잔여 node.exe 종료 (`scripts/stop-server.ps1` 호출) | 필수 (없으면 일부 자식 프로세스 못 죽임) |
| `pull_and_install.bat` | `git pull` + `package.json`/lock 변경 시에만 `npm install` | — |
| `restore_server.bat` | `restore/` 폴더 최신 zip → stop_server → 3초 대기 → CLI 복원 → start_server | 필수 |
| `rollback_server.bat` | 직전 복원의 `.bak.*` 4개(`app.db`, `app.db-wal`, `app.db-shm`, `.env`)를 각각 가장 최근 timestamp로 자동 롤백 | 필수 |
| `backend/scripts/restore-from-file.ts` | CLI 복원 본체. port 3000 listening 가드 + `restoreBackup(buffer)` 호출 | — (배치가 권한 보장) |
