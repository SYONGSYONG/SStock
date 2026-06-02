# 04-tasks.md — MVP 진행 체크리스트

## 진행 규칙

> 아래 규칙을 위반하면 작업을 중단하고 원인을 해결한 뒤 재진행한다.

1. **순서 엄수** — 단계 번호 순서대로만 진행한다. 건너뜀 금지.
2. **병렬 금지** — 한 단계가 완전히 완료된 후 다음 단계로 이동한다.
3. **단계별 검증 필수** — 검증 방법을 실제로 실행하여 통과 확인 후 ✅ 체크.
4. **확장 단계 제외** — 이 문서는 MVP 범위만 다룬다. 확장 기능은 별도 문서에서 관리한다.

---

## Phase 1 — 설계 (현재 진행 중)

목표: 개발 착수 전 모든 결정을 문서로 확정한다.

| # | 단계 | 작업 내용 | 검증 방법 | 상태 |
|---|------|----------|----------|------|
| 1 | CLAUDE.md 작성 | 역할·절대규칙·기술스택·폴더구조 정의 | 절대규칙 8개 모두 포함 여부 육안 확인 | ✅ |
| 2 | 00-overview.md 작성 | 프로젝트 개요, 6개 문서 매핑표, 읽는 순서, 관심사 분리 원칙 | 매핑표 6행 완성, 읽는 순서 명시 여부 확인 | ✅ |
| 3 | 01-product.md 작성 | 제품 목표, 페르소나, MVP 기능 3개, 이슈 필드, 칸반 상태 전환, 자동 댓글 규칙 | 상태 전환 9가지 전부 포함, PENDING 진출입 규칙 명시 여부 확인 | ✅ |
| 4 | 02-specs.md 작성 | 기술스택 확정, DB 스키마 5개, API 엔드포인트, 테스트 전략, 환경변수 목록 | 테이블 5개·API 엔드포인트 전체·`.env.example` 키 목록 포함 여부 확인 | ✅ |
| 5 | 03-design.md 작성 | 설계 결정 8개 (선택/대안/근거/트레이드오프), 색상 코드, 와이어프레임 | 결정 8개 모두 트레이드오프 항목 존재, 색상 코드표 포함 여부 확인 | ✅ |
| 6 | 04-tasks.md 작성 | Phase 3개, 총 28단계 체크리스트, 단계별 검증 방법, 진행 규칙 | Phase 1 10단계·Phase 2 10단계·Phase 3 8단계 개수 확인 | ✅ |
| 7 | 05-conventions.md 작성 | 네이밍 컨벤션(파일·변수·컴포넌트), 폴더 구조 규칙, Git 브랜치 전략, 코드 스타일 | 백엔드·프론트엔드 네이밍 규칙 각각 명시, 브랜치 전략 포함 여부 확인 | ✅ |
| 8 | 페이지 명세 보완 | 각 페이지 URL·구성 컴포넌트·데이터 흐름·상태 관리 정의 → `doc/06-pages.md` 생성 | 3개 페이지 URL 전부 정의, 슬라이드 오버 동작 명세, 라우터 구성 포함 여부 확인 | ✅ |
| 9 | 문서 교차 검토 | 7개 문서 간 용어·수치·규칙 일관성 점검 | 모순 항목 0개. 전체 문서 `TO DO` 표기로 통일 완료 | ✅ |
| 10 | 원격 저장소 Push | 전체 문서를 GitHub `main` 브랜치에 push | `git log --oneline` 으로 커밋 히스토리 확인, GitHub 웹에서 파일 존재 확인 | ✅ |

---

## Phase 2 — 백엔드

목표: 프론트엔드 없이 API만으로 모든 비즈니스 로직이 동작하는 상태를 만든다.

| # | 단계 | 작업 내용 | 검증 방법 | 상태 |
|---|------|----------|----------|------|
| 1 | 백엔드 프로젝트 초기화 | `backend/` 폴더 생성, Node.js + TypeScript + Express 설치, `tsconfig.json`, `package.json` 스크립트 구성 | `GET /health` → `{"status":"ok"}` 확인 | ✅ |
| 2 | DB 초기화 | better-sqlite3 v11(Node24 지원), WAL 모드, 테이블 5개 `CREATE IF NOT EXISTS` 스크립트 | 서버 기동 시 DB 파일 생성, 테이블 5개 존재 확인 | ✅ |
| 3 | 환경 변수 설정 | `.env.example` 키 목록, `dotenv` 로드, `backend/.gitignore`에 `.env`·`data/` 등록 | `git status`에서 `.env` 미추적 확인 | ✅ |
| 4 | 팀원 API | `GET /api/members`, `POST /api/members` 구현 | `members.test.ts` 3개 통과 | ✅ |
| 5 | 이슈 API | `GET /api/issues`, `POST /api/issues`, `GET /api/issues/:id`, `PATCH /api/issues/:id` 구현 | `issues.test.ts` 8개 통과 | ✅ |
| 6 | 댓글 API | `GET /api/issues/:id/comments`, `POST /api/issues/:id/comments` 구현 | `comments.test.ts` 4개 통과 | ✅ |
| 7 | 칸반 API + 상태 전환 로직 | `GET/POST /api/kanban`, `PATCH /api/kanban/:issueId/:org/:repo/status`, `ALLOWED_TRANSITIONS` 기반 검증 | `kanban.test.ts` 16개 통과, 금지 전환 400 확인 | ✅ |
| 8 | 상태 전환 로그 + 자동 댓글 | 전환 시 `transition_logs` INSERT, 담당자 멘션 자동 댓글 생성 | `transition.test.ts` 4개 통과, 로그 불변성 확인 | ✅ |
| 9 | GitHub API 연동 | `@octokit/rest` 설치, `/api/repos` + `/api/repos/:org/:repo/commits`, 5분 캐시 | 실제 토큰 설정 후 `SYSTEM3-SW/Framework5.0` 데이터 반환 확인 | ✅ |
| 10 | 백엔드 통합 테스트 전체 실행 | `npm run test` 5개 파일 전체 실행 | **35개 테스트 전부 통과, 실패 0건** | ✅ |

---

## Phase 3 — 프론트엔드

목표: 백엔드 API와 연동하여 브라우저에서 모든 기능이 동작하는 상태를 만든다.

| # | 단계 | 작업 내용 | 검증 방법 | 상태 |
|---|------|----------|----------|------|
| 1 | 프론트 프로젝트 초기화 | Vite React19+TS, Tailwind3, `useTheme` 훅, localStorage 테마 유지 | 테마 토글 동작, localStorage 값 유지 | ✅ |
| 2 | 레이아웃 + 사이드바 + 라우터 | React Router v7, AppLayout, Sidebar(레포 트리), ThemeToggle | URL 이동, 사이드바 렌더링 | ✅ |
| 3 | 대시보드 페이지 | RepoCard + 커밋 히스토리 5건, GitHub 외부 링크 버튼 | `/api/repos` + commits 연동 | ✅ |
| 4 | 이슈 게시판 페이지 + 등록 폼 | 이슈 테이블, StatusBadge, 상태 필터, IssueForm 모달 | `IssueForm.test.tsx` + `StatusBadge.test.tsx` 21개 통과 | ✅ |
| 5 | 이슈 슬라이드 오버 패널 | Radix Dialog 기반 IssueDetailSheet, 댓글, 칸반 등록 | 이슈 클릭 시 패널 오픈, 댓글·칸반 등록 동작 | ✅ |
| 6 | 칸반 보드 페이지 | dnd-kit 드래그앤드롭, 4컬럼, TransitionButton 병행 | `KanbanBoard.test.tsx` + `TransitionButton.test.tsx` 통과, 금지 전환 버튼 미노출 | ✅ |
| 7 | 슈퍼 레포 칸반 통합 뷰 | isUnified 플래그, 레포별 색상 테두리, 레포명 태그 | KanbanBoard 통합 뷰 렌더링 테스트 통과 | ✅ |
| 8 | 프론트 전체 테스트 + 빌드 | `npm run test` 4파일 21개 통과, `npm run build` 성공 | **21개 테스트 통과, 빌드 에러 0건** | ✅ |

---

---

## Phase 4 — 기능 확장

목표: MVP 이후 추가된 기능들. 모두 구현 완료 상태.

| # | 기능 | 주요 변경 파일 | 상태 |
|---|------|--------------|------|
| 1 | To Do 게시판 분리 | `issues.type` 컬럼 추가, `/todos` 라우트, `IssueBoardPage(type='todo')` | ✅ |
| 2 | 이슈/To Do 종결·되살리기 | `issues.is_closed` 컬럼, `closeIssue`, `reviveIssue` 서비스, 상세 페이지 버튼 | ✅ |
| 3 | 이슈 삭제 | `deleteIssue` (연쇄 삭제), 게시판 hover 삭제 버튼 | ✅ |
| 4 | 칸반 등록 해제 | `DELETE /api/kanban/:issueId/:org/:repo`, 상세 페이지 해제 버튼 | ✅ |
| 5 | 게시판 필터 + 검색 | 레포·상태 필터, 텍스트 검색(제목/제목+내용/의뢰자/담당자) | ✅ |
| 6 | 이슈 상세 → 별도 페이지 | `/issues/:id`, `/todos/:id`, `IssueDetailPage` | ✅ |
| 7 | 칸반 카드 팝업 | `KanbanCardPopup` (Radix Dialog, 읽기 전용), 게시판 이동 버튼 | ✅ |
| 8 | 칸반 이슈/To Do 타입 필터 | `typeFilter` 탭 (전체/이슈/To Do), To Do 카드 emerald 스타일 | ✅ |
| 9 | 대시보드 정렬 | 이름/날짜 오름차순·내림차순 정렬, `SortIcon` 컴포넌트 | ✅ |
| 10 | 대시보드 팝업 — README 뷰어 | ReactMarkdown, 상대 링크 자동 변환, 커밋 상세 내비게이션 | ✅ |
| 11 | 대시보드 팝업 — ZIP/GitHub/Clone 버튼 | 확인 다이얼로그, `POST /api/repos/:org/:repo/clone` | ✅ |
| 12 | 댓글 작성자 지정 | 멤버 선택 드롭다운, `author_name` JOIN, localStorage 마지막 선택 기억 | ✅ |
| 13 | 칸반 복수 레포 동시 등록 + 연관 레포 표시 | 체크박스 다중 선택, `other_repos` 서브쿼리, 파란 태그 표시 | ✅ |
| 14 | 서버 시작/종료 스크립트 | `start.vbs`, `start.ps1`, `stop_server.bat`(구 `stop.bat`), `stop.ps1` (PID 트리 종료) | ✅ |
| 15 | getById assignee_name 누락 수정 | `LEFT JOIN members` 추가, 칸반 팝업 담당자 정상 표시 | ✅ |

---

---

## Phase 5 — 회원관리 및 인증 시스템

목표: 개인 계정 기반 인증, 역할별 권한 분리, 회원 관리 기능 추가

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | DB 스키마 확장 | members 테이블에 소속·직급·전화번호·이메일·비밀번호·역할 컬럼 추가, issues에 requester_id 추가, MASTER 계정 자동 생성 | ✅ |
| 2 | 백엔드 auth 서비스 | login, register, changePassword, resetPassword 서비스 구현 | ✅ |
| 3 | auth 미들웨어 | requireAuth, requireTeamMember, requireAdmin 미들웨어 업데이트 | ✅ |
| 4 | auth 라우터 | POST /login, /register, /reset-request, GET /me, PATCH /password | ✅ |
| 5 | members 라우터 업데이트 | 프로필 수정, 역할 변경, 비밀번호 초기화, 삭제 엔드포인트 | ✅ |
| 6 | issues/comments 권한 적용 | 이슈 등록 시 requester 자동 설정, 삭제 권한 체크, 댓글 삭제 엔드포인트 추가 | ✅ |
| 7 | 칸반 권한 적용 | 상태 전환 team_member/admin 전용 제한 | ✅ |
| 8 | 프론트엔드 AuthContext | JWT 기반 인증 상태 관리, localStorage 유지 | ✅ |
| 9 | 로그인/회원가입 페이지 | LoginPage, RegisterPage, 비밀번호 초기화 요청 | ✅ |
| 10 | 프로텍티드 라우트 | 미인증 시 /login 리다이렉트, App.tsx 업데이트 | ✅ |
| 11 | 회원관리 페이지 | MembersPage (역할 변경, 초기화 요청 목록, 삭제) | ✅ |
| 12 | 프로필 수정 페이지 | ProfilePage (내 정보 수정, 비밀번호 변경) | ✅ |
| 13 | 이슈/댓글 연동 | 이슈 등록 의뢰자 자동 설정, 댓글 작성자 자동 설정, 댓글 삭제 UI | ✅ |
| 14 | 칸반 UI 권한 적용 | 비팀원은 드래그 비활성화, 로그인 사용자 칸반 전환 전달 | ✅ |
| 15 | AppLayout·Sidebar 업데이트 | 현재 로그인 사용자 표시, 로그아웃, 회원관리 메뉴 | ✅ |

---

## 진행 현황 요약

| Phase | 총 단계 | 완료 | 진행률 |
|-------|--------|------|-------|
| Phase 1 — 설계 | 10 | 10 | 100% ✅ |
| Phase 2 — 백엔드 | 10 | 10 | 100% ✅ |
| Phase 3 — 프론트엔드 | 8 | 8 | 100% ✅ |
| Phase 4 — 기능 확장 | 15 | 15 | 100% ✅ |
| Phase 5 — 회원관리 및 인증 | 15 | 15 | 100% ✅ |
| Phase 6 — Electron 데스크톱 앱 | 5 | 5 | 100% ✅ |
| Phase 7 — 활동 로그 | 4 | 4 | 100% ✅ |
| Phase 8 — 회원가입 승인 워크플로우 | 6 | 6 | 100% ✅ |
| Phase 9 — Electron 패키징 정비 + 운영 보강 | 5 | 5 | 100% ✅ |
| Phase 10 — 회원가입 거절·본인 취소 워크플로우 | 5 | 5 | 100% ✅ |
| Phase 11 — Electron 포커스 이슈 (native dialog 제거) | 2 | 2 | 100% ✅ |
| Phase 12 — 회원관리 진입 지연 / Electron 동적 base 통합 | 2 | 2 | 100% ✅ |
| Phase 13 — 회원관리 SWR 캐시 (즉시 표시 + 로딩/에러 명시) | 3 | 3 | 100% ✅ |
| Phase 14 — 버전 표시 + 메이저 불일치 경고 | 3 | 3 | 100% ✅ |
| Phase 15 — 로그인 유지 체크박스 (세션/영구 저장 선택) | 3 | 3 | 100% ✅ |
| Phase 16 — 버전 관리 규칙 (SemVer) | 1 | 1 | 100% ✅ |
| Phase 17 — 로그인 화면 버전/서버 주소 표시 | 2 | 2 | 100% ✅ |
| Phase 18 — 데이터 백업 / 복원 (서버 이전 대비) | 6 | 6 | 100% ✅ |
| Phase 19 — 운영 보호 + 백업 견고화 + 강제 비밀번호 변경 | 8 | 8 | 100% ✅ |
| Phase 20 — 보안 강화 + 코드 품질 개선 | 7 | 7 | 100% ✅ |
| Phase 21 — 데이터 무결성 + 웹 클론 정리 | 3 | 3 | 100% ✅ |
| **전체** | **123** | **123** | **100% 🎉** |

---

## Phase 6 — Electron 데스크톱 앱 (electron 브랜치)

목표: 기존 웹앱·백엔드 유지, Windows 데스크톱 앱 추가 (클론 폴더 선택 + 향후 로컬 git 관리 확장 기반)

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | electron/ 폴더 구성 | package.json, electron + electron-builder 설치 | ✅ |
| 2 | main.js | BrowserWindow 생성, dialog:openFolder, git:clone ipcMain 핸들러 | ✅ |
| 3 | preload.js | contextBridge로 electronAPI 노출 (isElectron, openFolderDialog, cloneRepo) | ✅ |
| 4 | 백엔드 clone-url API | GET /api/repos/:org/:repo/clone-url (토큰 포함 URL 반환, main process 전용) | ✅ |
| 5 | 프론트 분기 처리 | DashboardPage: window.electronAPI 감지 → 폴더 다이얼로그/텍스트 입력 자동 분기 | ✅ |

**실행 방법:**
- 개발: 백엔드·프론트 서버 실행 후 `start_electron.bat`
- 빌드(설치파일): `build_electron.bat`

---

## Phase 7 — 활동 로그 (electron 브랜치)

목표: 로그인 사용자의 모든 주요 동작을 텍스트 파일에 기록한다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | activity-log 서비스 | `backend/src/services/activity-log.ts` — 타임스탬프·카테고리 포맷, appendFileSync | ✅ |
| 2 | 인증 로그 | 로그인 성공/실패, 로그아웃 — auth-router.ts + `POST /api/auth/logout` 추가 | ✅ |
| 3 | 이슈·댓글 로그 | 이슈 등록/수정/삭제/종결/되살리기, 댓글 추가/삭제 — issues-router.ts | ✅ |
| 4 | 칸반·회원 로그 | 칸반 등록/해제/상태변경, 회원 역할변경/초기화/삭제 — kanban-router.ts, members-router.ts | ✅ |

**로그 파일:** `backend/logs/activity.log`

**로그 형식 예시:**
```
[2026-05-17 14:30:25] [LOGIN  ] 김시홍(admin) 로그인 성공 (shkim@example.com)
[2026-05-17 14:31:00] [LOGOUT ] 김시홍(admin) 로그아웃
[2026-05-17 14:32:10] [ISSUE  ] 김시홍(admin) #5 이슈 등록 — '로그인 버그'
[2026-05-17 14:33:00] [COMMENT] 테스터(team_member) 이슈 #5 댓글 #12 추가
[2026-05-17 14:34:00] [KANBAN ] 테스터(team_member) 이슈 #5 상태 변경 (repo) — TO DO → DOING
[2026-05-17 14:35:00] [MEMBER ] 김시홍(admin) 역할 변경 — 테스터: member → team_member
```

---

## Phase 8 — 회원가입 승인 워크플로우

목표: 회원가입은 즉시 활성이 아니라 관리자 승인을 거친 후에만 로그인 가능하도록 한다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | auth-service 수정 | `register()` INSERT 시 `is_active=0` 명시. `login()` 비밀번호 검증 통과 후 `is_active=0`이면 403 `PENDING_APPROVAL` 반환 | ✅ |
| 2 | 승인 엔드포인트 | `POST /api/members/:id/approve` (admin 전용, ActivityLog `회원가입 승인` 기록) | ✅ |
| 3 | LoginPage UI | `승인 대기` 메시지 분기, amber 알림 박스로 별도 표시 | ✅ |
| 4 | RegisterPage UI | 가입 완료 다이얼로그를 "관리자 승인 후 로그인 가능"으로 변경 | ✅ |
| 5 | MembersPage UI | 상단에 회원가입 승인 대기 collapsible 섹션 (이름·소속 헤더, 펼치면 직급·전화·이메일·신청일). 본 테이블에 "대기" 뱃지 + opacity dim | ✅ |
| 6 | Playwright E2E | 가입 → 로그인 거부 → admin 승인 → 로그인 성공 전 단계 검증 | ✅ |

**활동 로그 추가 이벤트 (Phase 7 보완 포함):**
- 회원가입 (`회원가입 — 이름 (이메일)`)
- 비밀번호 변경 (`이름(role) 비밀번호 변경`)
- 비밀번호 초기화 요청 (`비밀번호 초기화 요청 — 이메일`)
- 프로필 수정 (`이름(role) 프로필 수정 — 필드명 목록`)
- 회원가입 승인 (`admin(admin) 회원가입 승인 — 대상자`)
- 이슈 수정 시 제목·상태 변경 내용도 changes에 포함

**로그 파일 자동 로테이션:**
- `activity.log`가 10MB 초과 시 `activity.YYYY-MM-DD_HHMMSS.log`로 rename 후 새 파일에 이어 기록

---

## Phase 9 — Electron 패키징 정비 + 운영 보강

목표: 데스크톱 앱 첫인상 개선, 운영 사고 차단, 사용자 PC별 서버 IP 설정, 사이드바 실시간 알림.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | Electron 서버 IP 설정 페이지 | `/settings/server` 라우트 + `electronAPI.getConfig/setApiBase` + `%APPDATA%/Framework5.0_Manager/config.json` + 메뉴 `파일 > 서버 주소 변경` + `loadAppFromStart()`로 hash 초기화 | ✅ |
| 2 | 빌드 산출물 정비 | 출력 폴더 `Release/`, 인스톨러 `Framework5.0_Manager_Installer.exe`, 앱 본체 `Framework5.0_Manager.exe`, file:// 호환(vite `base: './'` + HashRouter) | ✅ |
| 3 | 앱 아이콘 | 프로텍 로고 256x256 정사각 패딩 변환 → `electron/build/icon.png`+`icon.ico` → `win.icon`/`installerIcon`/`uninstallerIcon`. 웹 `favicon.png`도 동일 적용 | ✅ |
| 4 | 마지막 admin 가드 + 사이드바 승인 대기 배지 | `PATCH /:id/role`·`DELETE /:id`에 활성 admin ≤ 1 가드(409 LAST_ADMIN). AuthContext에 `pendingCount`+`refreshPendingCount` 통합(60초 폴링 + MembersPage 액션 시 즉시 갱신), Sidebar는 표시만 | ✅ |
| 5 | 인스톨러 재빌드 배치 스크립트 | 루트 `build_electron.bat` — 이전 `Release/` 정리 → `frontend npm run build` → `electron npm run build` 순차 실행. 단계별 errorlevel 검사 + 결과 분기(`:missing` / `:end`) + `choice /T 5 /D N`으로 5초 자동 종료. 영문 메시지로 CMD CP949 환경에서도 깨짐 없이 출력 | ✅ |

**배포 가이드:**
- 인스톨러: `Release/Framework5.0_Manager_Installer.exe` 한 파일을 사용자 PC에 배포
- 서버 운영: 백엔드는 서버 PC 한 대에 PM2 또는 Windows 서비스로 24/7 운영
- 첫 실행: 서버 주소 입력 화면 → 백엔드 URL 입력 → 자동 로그인 화면 전환
- userData 위치: `%APPDATA%\Framework5.0_Manager\config.json` (서버 IP 저장소)
- 인스톨러 재빌드: 프로젝트 루트에서 `build_electron.bat` 더블클릭 (Windows 개발자 모드 필수 — symlink 권한). 출력: `Release/Framework5.0_Manager_Installer.exe`

---

## Phase 10 — 회원가입 거절·본인 취소 워크플로우

목표: 기존 "거절 = 즉시 삭제" 흐름을 바꿔, 거절은 상태로만 표시하고 본인이 직접 확인 후 취소해야 계정이 삭제되도록 한다. 거절당한 사람도 거절 사실을 알 수 있다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | DB + 서비스 | `members.rejected_at TEXT` 마이그레이션. `login()`에 `REGISTRATION_REJECTED` 403 분기(승인 대기보다 우선). `cancelRejectedRegistration()` — 이메일+비밀번호 재확인 후 본인이 자기 행 삭제 | ✅ |
| 2 | 백엔드 라우트 | `POST /api/members/:id/reject` (admin 전용, 삭제 대신 `rejected_at=NOW`). `POST /api/auth/cancel-registration` 신규. `approve`는 거절된 회원도 `rejected_at=NULL`로 복구 | ✅ |
| 3 | API 응답 보강 | `GET /api/members`, `/api/members/:id`, `/api/auth/me` 응답에 `rejected_at` 포함. 프론트 `Member` 타입에도 동일 필드 추가 | ✅ |
| 4 | 프론트 LoginPage | error 상태를 `none`/`pending`/`rejected`/`message` union으로 재구성. 거절 시 빨간 배너 + "가입 취소" 버튼(직전 입력한 이메일·비밀번호 보존). `ApiError` 클래스로 백엔드 `code` 보존 | ✅ |
| 5 | 프론트 MembersPage | 승인 대기 = `is_active=0 AND !rejected_at`로 좁힘. "거절" 버튼은 `deleteMember` 대신 `rejectMember` 호출. 본 목록 비활성 회원에 `대기`/`거절됨` 뱃지 분기 표시 | ✅ |

**Playwright E2E 검증 결과:**
- 가입 → 로그인(승인 대기 배너) → admin이 DB에 `rejected_at` 셋팅(테스트 편의) → 로그인(거절 배너 + 가입 취소 버튼) → 가입 취소 → DB에서 행 삭제 → 같은 이메일로 재가입 성공
- 스크린샷: `.TestScreenShot/01-login-rejected.png`

**활동 로그 추가 이벤트:**
- 회원가입 거절 (`admin(admin) 회원가입 거절 — 대상자`)
- 회원가입 본인 취소 (`회원가입 취소 (본인) — 이름 (이메일)`)
- 회원가입 승인이 거절 복구일 때는 액션명에 `(거절 복구)` 표기

---

## Phase 11 — Electron 포커스 이슈 (native dialog 제거)

목표: Electron BrowserWindow에서 `alert()`/`confirm()`이 닫힌 후 페이지 입력 포커스가 회복되지 않는 버그 해결. 가입 직후 LoginPage의 이메일/비밀번호 input을 첫 클릭에서 잡지 못하던 증상 차단.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | RegisterPage native alert 제거 | 가입 성공 시 `alert(...)` 호출 삭제. `navigate('/login', { state: { registered: true } })`로 안내 메시지 전달 | ✅ |
| 2 | LoginPage in-page 배너·인라인 확인 | error 상태 union에 `registered`/`cancelled`/`rejected_confirm` 추가. 거절 취소 흐름의 `confirm`/`alert`를 2단계 인라인 확인([확인]/[뒤로]) + cancelled 배너로 교체. location.state 소비 후 history 정리 | ✅ |

**검증:** Playwright로 가입 → LoginPage 진입 직후 emerald "회원가입이 접수되었습니다" 배너 표시 + 이메일/비밀번호 input 모두 첫 클릭에 즉시 포커스 (스크린샷 `.TestScreenShot/02-login-after-register.png`).

**관리자(MembersPage)의 `confirm`/`alert`는 Electron에서 같은 위험을 가질 수 있으나, 관리자 전용 화면이고 영향 범위가 좁아 별도 작업으로 남긴다.**

---

## Phase 12 — 회원관리 진입 지연 / Electron 동적 base 통합

목표: 관리자 회원관리 진입 시 보이던 수 초 딜레이의 원인인 중복 fetch 제거. 추가로 AuthContext의 `me` 호출이 빌드타임 `VITE_API_URL`을 쓰던 부분을 동적 base(`api/client.ts`의 `cachedBase`)로 통일.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | 회원관리 중복 fetch 제거 | AuthContext에 `updatePendingCount(count)` 신규 노출 — 호출자가 이미 가진 회원 리스트의 필터 결과 길이만 받아 추가 fetch 없이 카운트만 갱신. MembersPage.load()는 자기 `getMembers()` 결과로 `updatePendingCount(pending.length)` 호출하여 진입 시 `/api/members` 호출을 2회 → 1회로 축소. `refreshPendingCount`(자체 fetch)는 사이드바 60초 폴링용으로 유지. 거절 회원은 대기 카운트에서 제외하도록 필터도 MembersPage와 일치시킴 | ✅ |
| 2 | AuthContext `me` 동적 base 적용 | 기존 `fetch(\`${BASE}/api/auth/me\`)` (모듈 로드 시점 `import.meta.env.VITE_API_URL`) → `auth-api.ts`의 `getMe()` 사용으로 교체. `api/client.ts`의 `cachedBase`(Electron `config.json`의 `apiBase`)가 그대로 적용되어, 사용자가 메뉴에서 변경한 서버 IP가 즉시 반영됨 | ✅ |

**관련 파일:** `frontend/src/contexts/AuthContext.tsx`, `frontend/src/pages/MembersPage.tsx`, `doc/06-pages.md`

---

## Phase 13 — 회원관리 SWR 캐시 (즉시 표시 + 로딩/에러 명시)

목표: 관리자가 회원관리 페이지를 클릭하면 회원 목록이 즉시 표시되도록 한다. mount 직후 빈 배열 상태에서 "등록된 회원이 없습니다"가 잠깐 보였다가 응답 후 채워지는 깜빡임 제거.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | AuthContext SWR 캐시 | `cachedMembers: Member[] \| null` + `refreshMembers()` 신규. admin 로그인 직후 1회 + 60초 폴링으로 회원 목록을 캐시. `refreshPendingCount`는 `refreshMembers`의 별칭으로 유지(구버전 호환) | ✅ |
| 2 | MembersPage 즉시 렌더 | `useAuth().cachedMembers`로 초기 state를 채워 mount 직후 바로 렌더. mount 시 `reload()`로 백그라운드 refresh. `cachedMembers` 변화 시 useEffect로 화면 상태 따라 갱신 | ✅ |
| 3 | 로딩·에러 UI 분리 | 캐시가 없을 때만 `loading="회원 목록을 불러오는 중..."` 표시. 응답 실패 시 빨간 `loadError` 배너 명시 (기존 `.catch(()=>{})` 침묵 제거). 빈 목록과 로딩 중 상태가 분명히 구분됨 | ✅ |

**관련 파일:** `frontend/src/contexts/AuthContext.tsx`, `frontend/src/pages/MembersPage.tsx`, `doc/06-pages.md`

**적용에 새 빌드 필요**: 프론트엔드 변경이므로 Electron 데스크톱 앱에 반영하려면 `build_electron.bat`으로 인스톨러를 재빌드한 뒤 재배포해야 한다. dev 브라우저(Vite)에서는 즉시 반영된다.

---

## Phase 14 — 버전 표시 + 메이저 불일치 경고

목표: 어느 빌드가 떠 있는지 운영자가 즉시 확인할 수 있게 한다. 서버만 업그레이드되고 클라이언트는 옛 빌드일 때(또는 반대) 사고를 차단한다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | A. 백엔드 `/api/version` | `backend/src/app.ts`에 endpoint 추가. `backend/package.json` version + `git rev-parse --short HEAD` + 기동 ISO 시각을 모듈 로드 시점에 1회 계산해 응답. 인증 불필요 | ✅ |
| 2 | B. 클라이언트 버전 사이드바 표시 | `frontend/vite.config.ts`의 `define`으로 `__APP_VERSION__` 주입(타입은 `src/vite-env.d.ts`). `Sidebar.tsx` 하단에 `Client v…` + `Server v…` 표시, 툴팁으로 git SHA·서버 시작 시각 노출. `frontend/package.json`도 `1.0.0`으로 통일 | ✅ |
| 3 | C. 메이저 불일치 배너 | `VersionBanner.tsx` 신규 (`role="alert"`, `data-testid="version-mismatch-banner"`). mount 시 1회 + 5분마다 `getServerVersion()` 호출, 메이저(`split('.')[0]`)가 다르면 amber 배너 + 닫기 버튼. `App.tsx`의 routes 외부에 배치(공개 페이지에도 노출) | ✅ |

**검증 (Playwright):**
- 같은 메이저(서버=클라 v1.0.0): 배너 없음, 사이드바 "Client v1.0.0 / Server v1.0.0" 표시 (스크린샷 `.TestScreenShot/03-members-instant.png` 시점에 함께 노출)
- 메이저 불일치(서버 v2.0.0 / 클라 v1.0.0): 빨간 배너 표시 + 닫기 동작 (스크린샷 `.TestScreenShot/04-version-mismatch-banner.png`)

**파일:** `backend/src/app.ts`, `backend/package.json`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/vite-env.d.ts`, `frontend/src/api/version-api.ts`, `frontend/src/components/VersionBanner.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/App.tsx`

---

## Phase 15 — 로그인 유지 체크박스 (세션/영구 저장 선택)

목표: 기존 정책은 로그인 후 항상 24시간 `localStorage` 유지였음. 공용 PC 시나리오 대응을 위해 사용자가 매 로그인 시 선택 가능하게 한다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | api/client.ts | `readAuthToken()` 신규 — `localStorage` 우선, 없으면 `sessionStorage` fallback. `api()`가 이를 호출 | ✅ |
| 2 | AuthContext | `login(token, user, persist: boolean)` — 양쪽 저장소 정리 후 선택된 곳에만 저장. `loadFromStorage`와 `me` 호출도 양쪽 fallback. `logout` / 토큰 만료 시 `clearAllAuthStorage()`로 양쪽 모두 정리 | ✅ |
| 3 | LoginPage | "로그인 유지" 체크박스 (기본 OFF, `data-testid="remember-me"`). 체크 ON → 24시간 자동 로그인 / 미체크 → 앱·탭 종료 시 자동 로그아웃 | ✅ |

**검증 (Playwright):**
- 체크 OFF로 로그인 → `sessionStorage`에만 토큰·user 저장, `localStorage`는 비어 있음
- 체크 ON으로 로그인 → `localStorage`에만 저장, `sessionStorage`는 비어 있음
- 스크린샷: `.TestScreenShot/05-login-remember-me.png`

**적용에 새 빌드 필요**: Electron 데스크톱 앱 반영은 `build_electron.bat` 재실행.

---

## Phase 16 — 버전 관리 규칙 (SemVer)

목표: 시맨틱 버저닝(SemVer) 정책을 명시한다. 클라이언트·서버·Electron 인스톨러 모두 동일 체계를 사용하며, Phase 14의 메이저 불일치 배너와 한 묶음으로 운영된다.

**기준선: v1.0.0**

| 위치 | 의미 | 올리는 기준 |
|------|------|-------------|
| **1**.x.x | Major | 호환성이 깨지는 큰 변경 (DB 스키마 파괴적 변경, API 시그니처 변경, 인증 모델 교체 등) |
| x.**1**.x | Minor | 기존 기능과 호환되는 기능 추가 (새 엔드포인트·페이지·옵션 추가) |
| x.x.**1** | Patch | 버그 수정, 안정화, 작은 개선 (UI 미세 조정, 로깅 보강, 의존성 패치) |

**운영 정책: 단, 당분간 버전을 올리지 않는다.**
- v1.0.0 고정 유지. 위 표는 향후 올리게 될 시점의 판단 기준.
- 동기화 대상: `backend/package.json`, `frontend/package.json`, `electron/package.json` 세 파일의 `version` 필드를 항상 같은 값으로 유지.
- 올리는 시점이 오면 Git 태그(`v1.x.y`)도 함께 부착할지 별도 결정.

---

## Phase 17 — 로그인 화면 버전/서버 주소 표시

목표: 로그인 화면에서도 클라이언트·서버 버전과 현재 연결된 서버 주소를 확인할 수 있도록 한다. 사용자가 로그인 전에 어떤 빌드/서버를 보고 있는지 즉시 파악 가능.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | `VersionFooter` 공통 컴포넌트 추출 | Sidebar 하단 인라인 코드를 `frontend/src/components/VersionFooter.tsx`로 추출. `className`·`testId`·`showApiBase` prop. Sidebar는 이를 그대로 사용(testId `sidebar-version` 유지) | ✅ |
| 2 | LoginPage 하단에 VersionFooter 배치 | `showApiBase` 옵션 ON. 표시 우선순위: ① 서버 origin(`/api/version` 응답, Vite proxy 환경에서도 정확) ② Electron config의 raw API base ③ `window.location.origin`. **Electron 환경에서만 노출** (브라우저에서는 같은 origin이라 표시 안 함) | ✅ |

**백엔드 확장:** `/api/version` 응답에 `host`/`origin` 필드 추가. `req.headers.host` + `req.protocol` 기반이라 Vite proxy 환경(클라 5173 → 백엔드 3000)에서도 실제 백엔드 origin 반환.

**검증 (Playwright, dev 브라우저):**
- 로그인 화면 하단: "Client v1.0.0 / Server v1.0.0" 표시 (브라우저 환경이라 "현재서버" 줄 미노출). 스크린샷 `.TestScreenShot/08-login-version-browser-no-apibase.png`.
- Electron 빌드에서는 "현재서버 : http://localhost:3000" 형식(ServerSettingsPage 입력값과 동일)으로 한 줄 추가 노출 (다음 인스톨러 빌드 후 확인).

**적용에 새 빌드 필요**: Electron 데스크톱 앱 반영은 `build_electron.bat` 재실행.

---

## Phase 18 — 데이터 백업 / 복원 (서버 이전 대비)

목표: admin이 운영 데이터(DB + .env)를 zip 한 파일로 묶어 다운로드하고, 새 서버에서 그대로 복원할 수 있다. **`.env`를 git에 올리지 않으면서도 서버 이전을 무중단으로 진행**하는 게 핵심 목적.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | 의존성 추가 | `adm-zip`(zip 읽기/쓰기) + `multer`(파일 업로드) + 타입 정의 | ✅ |
| 2 | `backup-service.ts` 구현 | `createBackup(db)` — WAL checkpoint 후 `app.db`+`.env`+`meta.json`을 zip으로 묶어 Buffer 반환. `restoreBackup(buffer, db)` — zip slip 방지(허용 항목 화이트리스트, `..`/경로 분리자 금지), `schemaVersion` 검증, `db.close()` 후 파일 교체, 실패 시 `*.bak.<ts>` 롤백 | ✅ |
| 3 | admin 라우터 엔드포인트 | `GET /api/admin/backup` (admin 전용, zip 응답, 활동 로그 기록) + `POST /api/admin/restore` (admin 전용, multipart, 100MB 상한, 복원 성공 시 응답 후 `process.exit(0)`로 외부 재기동 유도) | ✅ |
| 4 | 관리자 페이지 UI | `AdminPage.tsx`에 "데이터 백업 / 복원" 섹션 추가. 다운로드 버튼 + 파일 업로드 + 경고 안내(덮어쓰기·재시작·재로그인 필요) | ✅ |
| 5 | E2E 검증 | curl로 백업 zip 받기 → 같은 zip 업로드 → `restoredDb:true`, `restoredEnv:true` 응답 + 서버 자동 종료 확인 | ✅ |
| 6 | 문서 갱신 | `02-specs.md` API 표 + "데이터 백업 / 복원" 섹션 추가. "최초 설치 절차"의 `.env`를 필수로 격상, "자주 발생하는 오류"에 "레포 로딩 무한 스피너 → `.env` 누락" 케이스 추가 | ✅ |

**보안 결정**: `.env`는 시크릿(GITHUB_TOKEN, JWT_SECRET) 포함이라 **git에 올리지 않는다**. 대신 백업 zip에 담아 관리자만 다운로드 가능하게 제한. 백업 파일 자체는 사내 안전 채널로 이관 권장.

**Windows 제약 대응**: 살아있는 SQLite의 WAL 파일은 잠금 상태라 rename 불가 → 복원 직전 `db.close()` 호출 후 파일 교체, 응답 직후 프로세스 종료. `start_server.bat`이 다시 띄우면 새 DB로 가동.

**Phase 19에서 해소된 항목**: 백업 보관 기간 정책(`.bak` 7일 자동 정리), 운영 보호(JWT 가드, CORS 화이트리스트, graceful shutdown).

**여전히 미반영 (Phase 20+ 후보)**:
- 자동 백업 스케줄러 (예: 매일 03:00 zip 생성 후 S3/SMB로 전송)
- 백업 파일 자체 암호화 (시크릿 노출 위험 완화)
- 복원 후 자동 재기동 (Windows 서비스 또는 PM2 supervisor 도입)

---

## Phase 19 — 운영 보호 + 백업 견고화 + 강제 비밀번호 변경

목표: 운영 배포 직전 보안 가드를 추가하고, 백업/복원의 신뢰성을 끌어올린다. 초기 1234 암호 잔존 문제를 강제 변경 흐름으로 해결.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | 백업 견고화 | `backup-service`에 SHA256 체크섬·BEGIN IMMEDIATE 락·`.bak` 7일 자동 정리·EBUSY retry(200ms × 25)·롤백 실패 상세 보고·`ENV_FILE_PATH` override. `restore-from-file.ts`에 port 3000 listening 가드. `stop_server`를 `scripts/stop-server.ps1`로 분리하고 net session 권한 경고 추가 | ✅ |
| 2 | 운영 가드 (보안) | `config.ts` 신규 — `NODE_ENV=production`에서 JWT_SECRET 미설정/32자 미만/기본 패턴 포함 시 부팅 차단. `app.ts`에 CORS 콤마 구분 화이트리스트(미설정 시 localhost dev만) | ✅ |
| 3 | 운영 가드 (안정성) | `index.ts`에 SIGTERM/SIGINT/uncaughtException/unhandledRejection 핸들러 → graceful path로 `server.close → wal_checkpoint → db.close → exit`. 10초 강제 종료 fallback | ✅ |
| 4 | DB 마이그레이션 추적 | `schema_migrations` 테이블 + `MIGRATIONS` 배열. 기존 ALTER 11개를 v1~v4로 backfill, 인덱스 6개(v6) 일괄 생성 | ✅ |
| 5 | 초기 비밀번호 강제 변경 | `members.password_change_required` 컬럼(v5) + master 자동 생성 시 1. `login`/`/me` 응답에 노출. `changePassword`에서 0으로 reset, `resetPasswordToDefault`에서 1로. 프론트 `ForceChangePasswordPage` + `ProtectedRoute` 분기 + `AuthContext.markPasswordChanged` | ✅ |
| 6 | 이슈 본문 수정 + 댓글 수정 | `issues-service.update`에 title/content 정식 지원(빈 입력 400). 라우터 PATCH 로그에서 status dead-code 제거. 댓글 `PATCH /api/issues/:id/comments/:commentId` 신규(작성자·admin만, is_system 보호). 프론트 IssueDetailPage에 이슈 본문 수정 모드 + 댓글 인라인 수정 | ✅ |
| 7 | 테스트 보강 | `backup.test.ts` 신규 8개(라운드트립, 체크섬 변조 거부, zip slip 방어, 스키마 mismatch, .bak 정리 등). issues에 제목/본문 수정 + 빈 입력 케이스. comments에 수정 권한/시스템 보호. **총 61개 통과** | ✅ |
| 8 | 문서 갱신 | `02-specs.md` API 표 + 운영 보호 표 + 백업 안전장치 표 + 운영 도구 표 + 테스트 표 + 환경변수(NODE_ENV/CORS/JWT) 보강. `04-tasks.md`에 본 Phase 19 추가 | ✅ |

**CLAUDE.md 9번 규칙 준수**: `password_change_required` 컬럼은 `DEFAULT 0`이라 기존 admin 영향 없음. 새 마스터(admin=0명)만 1로 자동 set. `meta.hashes`는 optional이라 옛 백업도 통과(하위 호환).

---

## Phase 20 — 보안 강화 + 코드 품질 개선

목표: 코드 점검에서 도출된 보안 결함·코드 스멜을 일괄 정리한다. 배포 전이라 하위호환 부담 없이 레거시까지 완전 제거.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | 인증 가드 보강 + silent failure 제거 | `POST /api/admin/login` 백도어 라우트 제거(1234 기본 비번 admin JWT 무단 발급 차단). `POST /api/repos/.../clone`에 `requireTeamMember` + 절대경로·`..` 차단. `clone-url` 권한 `requireAuth → requireAdmin` 격상(GITHUB_TOKEN 평문 노출 방지). `KanbanPage` 상태 전환 `alert()` → in-page 에러 배너(Phase 11 정책 준수). Dashboard/IssueBoard/Kanban/Profile의 `.catch(()=>{})` silent 실패 → 에러 배너 표시 | ✅ |
| 2 | helmet 보안 헤더 + 로그인 rate limit | `helmet` 도입(HSTS·nosniff·X-Frame-Options 등. CSP off, CORP cross-origin). `express-rate-limit`로 `POST /api/auth/login` 1분당 10회 제한(429 `RATE_LIMITED`, 테스트 환경 skip). 패키지 2개 사용자 승인 후 설치 | ✅ |
| 3 | JWT 시크릿 통합 + 에러 로깅 + gitignore | `getSecret()` 3곳 중복 → `config.getJwtSecret()` 단일 함수(런타임 평가 유지). `errorHandler`가 production에서 스택 전체 stdout 노출 차단(메시지만). `backend/.gitignore`에 `.env.bak.*` 추가 | ✅ |
| 4 | 프론트엔드 인증 계층 테스트 보강 | `client.test.ts` 신규(api 래퍼·readAuthToken·ApiError). `AuthContext.test.tsx` 신규(login persist 분기·logout·role 파생·markPasswordChanged·토큰 복원). 프론트 테스트 21 → 40개 | ✅ |
| 5 | 활동 로그 비동기화 + GitHub 캐시 LRU | `activity-log`의 `appendFileSync` → Promise 체인 직렬화 비동기 쓰기(순서 보장 유지). `repos-service` 캐시에 LRU eviction + 100개 상한(패키지 없이 Map 삽입 순서 활용) | ✅ |
| 6 | admin_settings 레거시 완전 제거 | 마이그레이션 v7 `DROP TABLE admin_settings`. `admin-service.ts`·`AdminPage.tsx`·`hooks/useAdmin.ts` 삭제. `admin-router` `/password` 라우트 제거. `admin-api`의 dead 함수(adminLogin/changePassword/createMemberAdmin/deleteMember) 제거. live 함수(getActivityLog/downloadBackup/restoreBackup) 유지 | ✅ |
| 7 | 비밀번호 정책 강화 | 8자 이상 + 영문자(대소문자 무관) 1자 + 숫자 1자, 특수문자·공백 불가. `auth-service.validatePassword()` register·changePassword 적용. 프론트 `lib/password.ts` 공통 유틸로 Register/ForceChange/Profile 즉시 검증. 정책 위반 5케이스 테스트 추가 | ✅ |

**테스트 현황**: 백엔드 61 → **67개**, 프론트엔드 21 → **40개** 전원 통과.

**커밋**: `507e015`(인증 가드) · `74baec4`(helmet/rate-limit) · `4a66364`(JWT/로깅/gitignore) · `b56c9ec`(프론트 테스트) · `76035b2`(로그/캐시) · `f50e95f`(admin_settings 제거) · `7579ce6`(비밀번호 정책)

**CLAUDE.md 규칙 준수**: 규칙 2(돌발 의존성) — helmet·express-rate-limit는 사용자 승인 후 설치. 규칙 9(스키마 하위호환) — `admin_settings` DROP은 배포 전 + 데이터 손실 OK를 사용자에게 확인 후 진행(현재 어떤 기능에서도 미사용인 레거시 테이블).

---

## Phase 21 — 데이터 무결성 + 웹 클론 정리

목표: 비즈니스 로직 계층 점검에서 발견된 데이터 무결성 위험을 보강하고, 웹에서 의미 없던 서버 클론 기능을 정리한다.

| # | 단계 | 주요 작업 | 상태 |
|---|------|---------|------|
| 1 | 데이터 무결성 보강 | 다단계 DB 변경(deleteIssue·closeIssue·kanban transition·register)을 `db.transaction()`으로 원자화. 회원 삭제 시 `issues.requester_id`/`comments.author_id`/`transition_logs.actor_id`까지 NULL 익명화해 FK RESTRICT로 막히던 문제 해결(활동 이력 있어도 삭제 가능). 미등록 칸반 해제를 일반 Error → `AppError(404)`로 교정. register는 중복 검증을 UPDATE보다 먼저 수행 | ✅ |
| 2 | N+1 쿼리 제거 + dead code 정리 | `issues-service.getAll`의 이슈별 칸반 쿼리(1+N) → IN 절 일괄 조회 + 그룹핑(2번 고정). 호출자 없는 `members-service.ts` 삭제 | ✅ |
| 3 | 웹 클론 → 명령어 복사 전환 | 웹 브라우저는 서버에 직접 클론하지 않고 `git clone <url>` 명령어 복사 UI 제공. Electron 로컬 클론은 유지. 백엔드 `POST /clone` 라우트 + `repos-service.cloneRepo`(서버 측 git clone 공격면) 제거. 클론 다이얼로그 버튼 라벨 '취소'→'닫기' | ✅ |

**테스트 현황**: 백엔드 67 → **69개**(회원 삭제 FK·칸반 해제 404 추가), 프론트엔드 **40개** 유지. 전원 통과.

**커밋**: `1a6c670`(데이터 무결성) · `21df781`(N+1·dead code) · `a5810b8`(웹 클론→명령어 복사) · `c86c54e`(다이얼로그 버튼 라벨)

**CLAUDE.md 규칙 준수**: 규칙 7(레포 무결성) — 클론은 사용자 PC(Electron) 또는 사용자 본인 터미널(명령어 복사)에서만 수행, 이 앱은 어떤 레포에도 쓰기 안 함. `transition_logs` 불변 원칙은 회원 삭제 시 `actor_id`만 NULL 익명화하는 예외를 둠(전환 사실·시각 기록은 보존).
