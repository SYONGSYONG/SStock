# 06-pages.md — 페이지 명세

> 각 페이지의 URL·구성 컴포넌트·데이터 흐름·상태 관리를 정의한다.
> 실제 구현 기준으로 유지 (설계 초안과 다를 수 있음).

---

## URL 구조 전체 맵

```
/login                     → 로그인 (공개, 최초 진입점)
/register                  → 회원가입 (공개)
/reset-password-request    → 비밀번호 초기화 요청 (공개)

/                          → 대시보드 (인증 필요)
/issues                    → 이슈 게시판 (인증 필요)
/issues/new                → 이슈 등록 페이지
/issues/:id                → 이슈 상세 페이지
/todos                     → To Do 게시판
/todos/new                 → To Do 등록 페이지
/todos/:id                 → To Do 상세 페이지
/repos/:repoName/kanban    → 칸반 보드 (레포별, 슈퍼 레포는 통합 뷰)
/members                   → 회원 관리 (admin 전용)
/logs                      → 활동 로그 뷰어 (admin 전용)
/profile                   → 내 프로필 수정
```

- 미인증 사용자가 보호 라우트 접근 시 `/login`으로 리다이렉트
- 로그인 성공 시 `/`으로 이동

- `:repoName` 예시: `Framework5.0` (슈퍼 레포), `PAccountsManager` (서브 레포)
- 슈퍼 레포 칸반(`/repos/Framework5.0/kanban`)은 모든 서브 레포 이슈를 통합 표시
- 이슈/To Do는 `IssueBoardPage`, `IssueNewPage`, `IssueDetailPage` 컴포넌트를 `type` prop으로 재사용

---

## 공통 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ Header: Framework5.0 Manager              [🌙 테마 토글] │
├──────────────┬──────────────────────────────────────────┤
│ Sidebar      │ <Page Content>                           │
│ (240px 고정) │                                          │
│  대시보드     │                                          │
│  이슈 게시판  │                                          │
│  To Do 게시판 │                                          │
│  팀원 관리    │                                          │
│  [레포 목록]  │                                          │
│  ├ 칸반보드   │                                          │
│  └ ...       │                                          │
└──────────────┴──────────────────────────────────────────┘
```

### 공통 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| `AppLayout` | `components/AppLayout.tsx` | 전체 레이아웃 래퍼 |
| `Sidebar` | `components/Sidebar.tsx` | 내비게이션 (레포 목록 포함). admin일 때 "회원 관리" 옆에 승인 대기 건수 emerald 배지 표시 (`useAuth().pendingCount`). 갱신 경로: ① AuthContext가 admin 로그인 직후 `refreshMembers()` 1회 + 60초 폴링으로 회원 목록 캐시(`cachedMembers`)·pendingCount 함께 유지 ② MembersPage 액션 직후 `reload()` → `refreshMembers()`로 캐시·화면 함께 갱신 ③ `updatePendingCount(count)`는 호출자가 이미 가진 리스트로 카운트만 갱신할 때 사용(예전 흐름 호환). 하단에 `<VersionFooter testId="sidebar-version">` 배치 |
| `VersionFooter` | `components/VersionFooter.tsx` | 클라이언트 빌드(`__APP_VERSION__`)와 서버 버전(`getServerVersion()`)을 두 줄로 표시. `showApiBase` prop이 true이고 **Electron 환경(window.electronAPI 존재)일 때만** "현재서버 : <server origin>" 한 줄 추가(브라우저에서는 무의미해 노출 안 함). API base 우선순위: ① 백엔드 `/api/version` 응답의 `origin`(요청을 받은 실제 host:port, Vite proxy 환경에서도 정확) ② 클라이언트 `getApiBase()` raw(Electron `config.json`의 사용자 입력) ③ `window.location.origin`. 포맷은 ServerSettingsPage 입력값(`http://host:port`)과 동일. `title` 속성에 git SHA·서버 시작 시각·API base(노출 시) 노출 |
| `Header` | `components/Header.tsx` | 앱 제목 + 테마 토글 |
| `StatusBadge` | `components/StatusBadge.tsx` | 칸반 상태 색상 뱃지 |

---

## PAGE 1 — 대시보드 (`/`)

| 항목 | 내용 |
|------|------|
| **목적** | 슈퍼 레포 + 서브 레포 전체 현황 확인. 레포 행 클릭 시 팝업으로 상세 확인 |

### 구성

```
DashboardPage
├── 레포 목록 테이블 (정렬: 이름▲▼ / 날짜▲▼)
│   └── RepoRow (클릭 → RepoDetailModal 열림)
└── RepoDetailModal (Radix Dialog)
    ├── 헤더: 레포 이름, [Clone] [ZIP] [GitHub] 버튼 (클릭 시 확인 다이얼로그)
    ├── [메인 뷰] README.md 뷰어 + 커밋 히스토리 (최신 10건)
    │   └── 커밋 행 클릭 → CommitDetailView (SHA, 작성자, 변경 파일 목록)
    └── [확인 다이얼로그] ZIP/GitHub/Clone 동작 전 확인
```

### 데이터 흐름

```
마운트
  → GET /api/repos
  → 각 레포 GET /api/repos/:org/:repo/commits (병렬, 최신 1건 미리보기)

레포 행 클릭 → 팝업 오픈
  → GET /api/repos/:org/:repo/commits (최신 10건)
  → GET /api/repos/:org/:repo/readme

커밋 행 클릭
  → GET /api/repos/:org/:repo/commits/:sha (상세)

Clone 확인
  → POST /api/repos/:org/:repo/clone { targetPath }
```

---

## PAGE 2 — 이슈 게시판 (`/issues`) / To Do 게시판 (`/todos`)

| 항목 | 내용 |
|------|------|
| **목적** | 전체 레포 통합 이슈/To Do 목록 조회·등록·필터·검색 |
| **컴포넌트** | `IssueBoardPage` (type='issue' 또는 'todo' prop) |

### 구성

```
IssueBoardPage
├── 헤더: 게시판 제목 + [이슈/To Do 등록] 버튼
├── 필터 바: [레포 선택▼] [상태 선택▼] [초기화] + 건수 표시
├── 검색 바: [검색필드▼ 제목/제목+내용/의뢰자/담당자] [검색어 입력]
└── 이슈 테이블 (고정 컬럼 너비)
    └── IssueRow (클릭 → /issues/:id 또는 /todos/:id 이동)
        ├── # (id)
        ├── 제목 (종결 시 취소선 + "종결" 뱃지)
        ├── 의뢰자 (최대 4글자)
        ├── 담당자 (최대 4글자)
        ├── 칸반 현황 (레포명: 상태 뱃지 목록)
        ├── 등록일
        └── 삭제 버튼 (hover 시 노출)
```

### 데이터 흐름

```
마운트
  → GET /api/repos (레포 필터 옵션용)
  → GET /api/issues?type=issue|todo (필터 적용)

필터/검색 변경 → 재조회 (서버 필터: repoKey, status, type / 클라이언트 필터: 검색어)

삭제 버튼 클릭
  → confirm 다이얼로그
  → DELETE /api/issues/:id → 재조회
```

---

## PAGE 3 — 이슈/To Do 등록 (`/issues/new`, `/todos/new`)

| 항목 | 내용 |
|------|------|
| **컴포넌트** | `IssueNewPage` (type prop) |

### 구성

```
IssueNewPage
├── 제목 입력
├── 상세 내용 입력
├── 의뢰자 입력 (텍스트)
└── [등록] 버튼 → POST /api/issues → /issues/:id 또는 /todos/:id 이동
```

---

## PAGE 4 — 이슈/To Do 상세 (`/issues/:id`, `/todos/:id`)

| 항목 | 내용 |
|------|------|
| **컴포넌트** | `IssueDetailPage` |

### 구성

```
IssueDetailPage
├── 뒤로가기 버튼 (→ /issues 또는 /todos)
├── 이슈 헤더 카드
│   ├── 제목, 의뢰자, 등록일, 칸반 상태 뱃지
│   ├── 종결 버튼 (DONE 또는 PENDING일 때만 활성)
│   └── 되살리기 버튼 (종결 상태일 때)
├── 본문 (읽기 전용)
├── 담당자·난이도 편집 (선택 + 저장)
├── 칸반 등록 현황 (레포명: 상태, 해제 버튼)
├── 칸반 등록 폼 (레포 체크박스 다중 선택 + 담당자 선택 필수)
└── 댓글 섹션
    ├── 댓글 목록 (작성자명, 내용, 시각. 시스템 댓글은 황색 italic)
    └── 댓글 입력 (작성자 선택 드롭다운 + 텍스트 영역 + 등록 버튼)
```

### 데이터 흐름

```
마운트
  → GET /api/issues/:id (담당자 JOIN 포함)
  → GET /api/issues/:id/comments (author_name JOIN 포함)
  → GET /api/members
  → GET /api/repos

칸반 등록
  → POST /api/kanban { issue_id, repo_key, assignee_id } (레포별 개별 요청)
  → 이슈·댓글 재조회

칸반 해제
  → DELETE /api/kanban/:issueId/:org/:repo
  → 이슈 재조회

종결
  → POST /api/issues/:id/close → 이슈 재조회

되살리기
  → POST /api/issues/:id/revive → 이슈 재조회

댓글 등록
  → POST /api/issues/:id/comments { content, author_id? }
  → 댓글 재조회
```

---

## PAGE 5 — 칸반 보드 (`/repos/:repoName/kanban`)

| 항목 | 내용 |
|------|------|
| **목적** | 칸반 4컬럼으로 이슈/To Do 상태 관리. 슈퍼 레포는 전체 통합 뷰 |

### 구성

```
KanbanPage
├── 헤더: 레포명 (통합 뷰 표시)
├── 타입 필터 탭: [전체 (N)] [이슈 (N)] [To Do (N)]
└── KanbanBoard (dnd-kit DndContext)
    ├── DroppableColumn (TO DO)
    │   └── DraggableCard[]
    │       ├── 제목 (클릭 → KanbanCardPopup)
    │       ├── 담당자 (@이름)
    │       ├── To Do 카드: emerald 배경 + TD 뱃지
    │       ├── [통합 뷰] 레포 태그 (색상 테두리)
    │       └── 연관 레포 태그 (파란 태그)
    ├── DroppableColumn (DOING)
    ├── DroppableColumn (DONE)
    └── DroppableColumn (PENDING)
└── KanbanCardPopup (Radix Dialog, 읽기 전용)
    ├── 이슈 타입 뱃지, 제목, 의뢰자, 담당자, 등록일, 난이도
    ├── 칸반 현황
    ├── 본문
    ├── 최근 댓글 (최대 3건)
    └── [닫기] [이슈/To Do 게시판으로 이동] 버튼
```

### 데이터 흐름

```
마운트
  → GET /api/kanban/:org/:repo?unified=true (슈퍼 레포) 또는 false (서브 레포)

드래그 드롭
  → PATCH /api/kanban/:issueId/:org/:repo/status { toStatus }
  → (서버) 전환 검증 → 전체 동기화 → 로그 → 자동 댓글
  → 칸반 재조회

카드 클릭
  → KanbanCardPopup 오픈 (GET /api/issues/:id + comments)
```

---

## PAGE 6 — 회원 관리 (`/members`, admin 전용)

| 항목 | 내용 |
|------|------|
| **목적** | 전체 회원 목록 조회, 역할 변경, 비밀번호 초기화, 삭제 |
| **접근** | `admin` 역할만 접근 가능 (`AdminRoute` 보호) |

### 구성

```
MembersPage
├── 회원가입 승인 대기 섹션 (대기 회원 ≥ 1명일 때, emerald 박스)
│   ├── 대기 = is_active=0 AND rejected_at IS NULL
│   └── 카드형 collapsible (대기자별)
│       ├── 접힌 헤더: ▶ "이름 : OOO, 소속 : OOO"   [승인] [거절]
│       └── 펼침 상세: 이름·소속·직급·전화번호·이메일·신청일 (dl/dt/dd)
├── 비밀번호 초기화 요청 알림 (요청 건수 > 0일 때, amber 박스)
│   └── 요청자별 [1234로 초기화] [거절] 버튼
└── 회원 목록 테이블
    ├── # / 이름 / 소속·직급 / 이메일 / 역할 뱃지(+상태 뱃지) / 가입일
    │   ├── is_active=0 행은 opacity dim
    │   ├── rejected_at IS NOT NULL → 빨간 "거절됨" 뱃지 (hover 시 거절일 표시)
    │   └── rejected_at IS NULL → emerald "대기" 뱃지
    └── 관리 컬럼 (admin만 표시)
        ├── member → [팀원 지정]
        ├── team_member → [팀원 해제] [관리자 지정]
        ├── admin → [관리자 해제]
        ├── [비번초기화] (모든 역할)
        └── [삭제]
```

### 데이터 흐름

```
마운트
  → useAuth().cachedMembers가 있으면 그것으로 즉시 렌더 (loading=false)
    없으면 빈 배열 + loading="회원 목록을 불러오는 중..." 표시
  → 동시에 useAuth().refreshMembers() 호출 (백그라운드 갱신)
  → cachedMembers가 갱신되면 useEffect로 화면 상태 따라 갱신
  → AuthContext가 admin 로그인 직후 + 60초 폴링으로 같은 캐시를 유지하므로
    회원관리 페이지 진입 시점엔 거의 항상 캐시가 채워져 있어 "즉시" 표시됨
  → 액션 직후에도 reload() → refreshMembers() 호출로 캐시·화면 함께 갱신

승인
  → POST /api/members/:id/approve → 재조회
  → 거절된 회원도 승인 시 rejected_at = NULL로 복구

거절
  → POST /api/members/:id/reject (삭제 아님) → 재조회
  → 본인이 가입 취소할 때까지 본 목록에 "거절됨" 뱃지로 유지

역할 변경
  → PATCH /api/members/:id/role { role } → 재조회
  → admin 강등 시 활성 admin ≤ 1이면 409 LAST_ADMIN (alert 표시)

비밀번호 초기화 수락
  → POST /api/members/:id/reset-password → 재조회

비밀번호 초기화 요청 거절
  → DELETE /api/members/:id/reset-request → 재조회

삭제
  → DELETE /api/members/:id → 재조회
  → 마지막 활성 admin이면 409 LAST_ADMIN (alert 표시)
```

---

## PAGE 7 — 활동 로그 (`/logs`, admin 전용)

| 항목 | 내용 |
|------|------|
| **목적** | `backend/logs/activity.log` 텍스트 파일을 웹 UI에서 조회 |
| **접근** | `admin` 역할만 접근 가능 (`AdminRoute` 보호) |

### 구성

```
LogsPage
├── 헤더: 줄 수 선택(100/200/500/1000/2000) + 카테고리 필터 + 자동 새로고침 토글 + [새로고침] 버튼
└── 로그 테이블 (font-mono, 최신순 정렬)
    ├── 시각 / 카테고리 뱃지 / 내용
    └── 카테고리 색상: LOGIN(green) / LOGOUT(slate) / ISSUE(blue) / COMMENT(violet) / KANBAN(orange) / MEMBER(red)
```

### 데이터 흐름

```
마운트 + 줄 수 변경
  → GET /api/admin/activity-log?lines=N (admin 전용)
  → 응답 lines 배열을 reverse() 하여 최신이 위로 오게 표시

자동 새로고침 ON
  → 10초 간격으로 동일 호출 반복
```

---

## PAGE 8 — 내 프로필 (`/profile`)

| 항목 | 내용 |
|------|------|
| **목적** | 본인 정보 수정, 비밀번호 변경 |
| **접근** | 로그인 사용자 전체 가능 |

### 구성

```
ProfilePage
├── 내 정보 수정 폼 (이름, 소속, 직급, 전화번호, 이메일)
└── 비밀번호 변경 폼 (현재 비밀번호, 새 비밀번호)
```

### 데이터 흐름

```
마운트
  → GET /api/auth/me

정보 수정
  → PATCH /api/members/:id { name, affiliation, position, phone, email }

비밀번호 변경
  → PATCH /api/auth/password { currentPassword, newPassword }
```

---

## PAGE 9 — 서버 주소 설정 (`/settings/server`, Electron 전용)

| 항목 | 내용 |
|------|------|
| **목적** | 데스크톱 앱 첫 실행 시 백엔드 서버 주소 입력. 이후 메뉴에서 재설정 가능 |
| **접근** | 인증 불필요. `window.electronAPI` 미존재(브라우저) 시 입력 비활성 안내 |

### 구성

```
ServerSettingsPage
├── 현재 설정값 표시 (있을 때)
├── URL 입력 (placeholder: http://192.168.0.10:3000)
└── [저장하고 다시 시작] 버튼
    → window.electronAPI.setApiBase(url)
    → main.js: config.json 저장 + loadAppFromStart() (hash 초기화)
    → HashRouter 첫 진입 → ProtectedRoute → /login
```

### 첫 진입 분기

`App.tsx`의 `ElectronBridge`가 Electron 환경에서 `isApiBaseConfigured()` 검사 후 설정 없으면 강제로 `/settings/server`로 navigate.

### 재설정

Electron 메뉴 `파일 > 서버 주소 변경...` → `mainWindow.webContents.send('navigate', '/settings/server')` → `electronAPI.onNavigate` → React Router navigate.

---

## 공개 페이지 (인증 불필요)

### 로그인 (`/login`)

```
LoginPage
├── 이메일 입력
├── 비밀번호 입력
├── [□] 로그인 유지 체크박스 (기본 OFF, 보안 우선)
│     · 체크: localStorage 저장 → 24시간 자동 로그인
│     · 미체크: sessionStorage 저장 → 앱·탭 종료 시 자동 로그아웃
├── 하단 풋터: <VersionFooter testId="login-version" showApiBase /> — Client/Server 버전 + (Electron 한정) "현재서버 : <서버 origin>" + 툴팁(git SHA·시작 시각·API base)
├── 상태(union: none/registered/cancelled/pending/rejected/rejected_confirm/message) 분기
│   ├── registered → emerald 박스 "회원가입이 접수되었습니다" (location.state 진입)
│   ├── cancelled  → slate 박스 "회원가입 신청이 취소되었습니다"
│   ├── message    → 빨간 텍스트 (입력 검증 실패, 잘못된 자격증명 등)
│   ├── pending(PENDING_APPROVAL)             → amber 박스 "관리자 승인 대기 중"
│   ├── rejected(REGISTRATION_REJECTED)       → 빨간 박스 + [가입 취소] 버튼
│   │                                            (직전 입력한 이메일·비밀번호 보존)
│   └── rejected_confirm → 빨간 박스 "정말 취소하시겠어요?" + [확인][뒤로] 2단계 인라인 확인
│         확인 시 POST /api/auth/cancel-registration → DB에서 본인 행 삭제 → kind='cancelled'
├── [로그인] 버튼 → POST /api/auth/login → JWT 저장 → / 이동
└── 링크: 회원가입 / 비밀번호 초기화 요청
```

> 에러 코드는 `frontend/src/api/client.ts`의 `ApiError`(status·code 보존)로 분기한다. 메시지 문자열 매칭 대신 `code`로 분기하므로 백엔드 메시지 변경에 강건하다.
>
> **native dialog 금지**: Electron BrowserWindow에서 `alert()`/`confirm()`이 닫힌 후 페이지 입력 포커스가 회복되지 않는 이슈가 있어, 가입 직후/취소 흐름의 모든 안내·확인은 in-page 배너와 2단계 인라인 확인으로 구현한다.

### 회원가입 (`/register`)

```
RegisterPage
├── 이름 / 소속 / 직급 / 전화번호 / 이메일 / 비밀번호 입력
└── [가입] 버튼 → POST /api/auth/register
    → navigate('/login', { state: { registered: true } })
    → LoginPage가 진입 직후 emerald 배너로 안내 (native alert 사용 금지)
```

### 비밀번호 초기화 요청 (`/reset-password-request`)

```
ResetPasswordRequestPage
├── 이메일 입력
└── [요청] 버튼 → POST /api/auth/reset-request → 관리자 처리 대기
```

---

## 라우터 구성

```typescript
// App.tsx
<BrowserRouter>
  <AuthProvider>
    <Routes>
      {/* 공개 라우트 */}
      <Route path="/login"                   element={<LoginPage />} />
      <Route path="/register"                element={<RegisterPage />} />
      <Route path="/reset-password-request"  element={<ResetPasswordRequestPage />} />

      {/* 보호 라우트 (ProtectedRoute: 미인증 시 /login 리다이렉트) */}
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index                              element={<DashboardPage />} />
        <Route path="/issues"                     element={<IssueBoardPage key="issues" type="issue" />} />
        <Route path="/issues/new"                 element={<IssueNewPage   key="issues-new" type="issue" />} />
        <Route path="/issues/:id"                 element={<IssueDetailPage key="issue-detail" />} />
        <Route path="/todos"                      element={<IssueBoardPage key="todos" type="todo" />} />
        <Route path="/todos/new"                  element={<IssueNewPage   key="todos-new" type="todo" />} />
        <Route path="/todos/:id"                  element={<IssueDetailPage key="todo-detail" />} />
        <Route path="/repos/:repoName/kanban"     element={<KanbanPage />} />
        <Route path="/profile"                    element={<ProfilePage />} />
        {/* AdminRoute: admin 역할 아니면 / 리다이렉트 */}
        <Route path="/members"                    element={<AdminRoute><MembersPage /></AdminRoute>} />
        <Route path="/logs"                       element={<AdminRoute><LogsPage /></AdminRoute>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </AuthProvider>
</BrowserRouter>
```

> `key` prop: `/issues` ↔ `/todos` 내비게이션 시 동일 컴포넌트(`IssueBoardPage`)가 재마운트되도록 강제해 이슈/To Do 혼용 버그를 방지한다.
