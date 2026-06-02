# 05-conventions.md — 개발 규칙

> 이 문서의 규칙은 CLAUDE.md 절대규칙과 동일한 효력을 가진다.
> 새 규칙 추가 또는 변경 시 팀 합의 후 이 문서를 먼저 수정한다.

---

## 1. 네이밍 컨벤션

### 공통

| 대상 | 규칙 | 예시 |
|------|------|------|
| 환경 변수 | `UPPER_SNAKE_CASE` | `GITHUB_TOKEN`, `JWT_SECRET` |
| 상수 | `UPPER_SNAKE_CASE` | `ALLOWED_TRANSITIONS`, `MAX_COMMIT_COUNT` |
| Boolean 변수·props | `is` / `has` / `can` 접두사 | `isSystem`, `hasAssignee`, `canTransition` |

### 백엔드 (Node.js + TypeScript)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | `kebab-case` | `issue-router.ts`, `kanban-service.ts` |
| 클래스 | `PascalCase` | `KanbanService`, `IssueRepository` |
| 함수·변수 | `camelCase` | `getIssueById`, `repoKey` |
| DB 테이블명 | `snake_case` (복수) | `issues`, `transition_logs`, `issue_kanban` |
| DB 컬럼명 | `snake_case` | `requester_id`, `is_system`, `transitioned_at` |
| API 경로 | `kebab-case` (복수 명사) | `/api/issues`, `/api/members`, `/api/kanban` |

### 프론트엔드 (React + TypeScript)

| 대상 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 파일 | `PascalCase.tsx` | `KanbanBoard.tsx`, `IssueForm.tsx` |
| 훅 파일 | `use` 접두사 + `camelCase` | `useIssues.ts`, `useTheme.ts` |
| 일반 유틸 파일 | `kebab-case.ts` | `api-client.ts`, `status-utils.ts` |
| 컴포넌트 함수 | `PascalCase` | `function KanbanBoard()` |
| props 타입 | 컴포넌트명 + `Props` | `KanbanBoardProps`, `IssueFormProps` |
| 커스텀 훅 | `use` 접두사 | `useIssues()`, `useKanban()` |
| CSS 클래스 | Tailwind 유틸리티만 사용. 커스텀 클래스명 금지 | |

---

## 2. 폴더 구조 규칙

임의 변경 금지. 구조 변경이 필요하면 CLAUDE.md 절대규칙 5번에 따라 승인 후 진행.

```
Framework5.0_Manager/
├── doc/                        # 프로젝트 문서 (00~05)
├── backend/
│   ├── src/
│   │   ├── __tests__/          # 테스트 파일 (*.test.ts)
│   │   ├── constants/          # 상수 (ALLOWED_TRANSITIONS 등)
│   │   ├── db/                 # DB 연결·스키마·마이그레이션
│   │   ├── middlewares/        # Express 미들웨어 (에러 처리, 인증)
│   │   ├── routes/             # 라우터 파일 (*-router.ts)
│   │   ├── services/           # 비즈니스 로직 (*-service.ts)
│   │   └── types/              # 공용 TypeScript 타입
│   ├── data/                   # SQLite .db 파일 저장 위치 (gitignore)
│   ├── .env                    # 시크릿 (gitignore)
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── __tests__/          # 테스트 파일 (*.test.tsx)
│   │   ├── api/                # 백엔드 호출 함수 (*-api.ts)
│   │   ├── components/         # 재사용 UI 컴포넌트
│   │   │   └── ui/             # shadcn/ui 자동 생성 컴포넌트 (수정 금지)
│   │   ├── hooks/              # 커스텀 훅 (use*.ts)
│   │   ├── pages/              # 페이지 단위 컴포넌트
│   │   └── types/              # 공용 TypeScript 타입
│   └── package.json
├── .env.example                # 키 목록만 (값 없음)
├── .gitignore
└── CLAUDE.md
```

### 파일 배치 원칙

| 파일 유형 | 위치 | 이유 |
|----------|------|------|
| GitHub API 호출 | `backend/src/services/` | 토큰이 백엔드에만 존재해야 함 |
| 상태 전환 매트릭스 | `backend/src/constants/kanban.ts` 단일 파일 | 프론트·백엔드 중복 정의 금지 |
| 공용 타입 | 각 `src/types/` | 프론트·백 간 타입 공유는 복사 허용 (모노레포 아님) |
| shadcn/ui 컴포넌트 | `frontend/src/components/ui/` | CLI 자동 생성 파일. 직접 수정하지 않음 |

---

## 3. Git 브랜치 전략

### 브랜치 구조

```
main          ← 항상 동작하는 상태 유지. 직접 push 금지.
└── phase/1-design     ← Phase 1 작업 브랜치
└── phase/2-backend    ← Phase 2 작업 브랜치
└── phase/3-frontend   ← Phase 3 작업 브랜치
    └── feat/kanban-board      ← 기능 단위 브랜치 (Phase 브랜치에서 분기)
    └── fix/transition-sync    ← 버그 수정 브랜치
```

### 브랜치 네이밍

| 접두사 | 용도 | 예시 |
|--------|------|------|
| `phase/` | Phase 단위 작업 | `phase/2-backend` |
| `feat/` | 새 기능 구현 | `feat/kanban-drag-drop` |
| `fix/` | 버그 수정 | `fix/kanban-sync-bug` |
| `docs/` | 문서만 수정 | `docs/update-conventions` |

### 커밋 메시지 형식

```
<type>: <한국어 요약> (50자 이내)

[선택] 본문: 변경 이유·맥락
```

| type | 용도 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 수정 |
| `test` | 테스트 추가·수정 |
| `refactor` | 동작 변화 없는 코드 개선 |
| `chore` | 빌드·설정 변경 |

**예시:**
```
feat: 칸반 상태 전환 API 구현
fix: PENDING → TO DO 전환 시 동기화 누락 수정
docs: 02-specs DB 스키마 transition_logs 설명 보완
test: kanban.test.ts 복수 칸반 동기화 케이스 추가
```

---

## 4. TypeScript 코드 스타일

### 공통 규칙

- `any` 타입 사용 금지. 불명확한 경우 `unknown` 사용 후 타입 가드 적용.
- `interface` 와 `type` 중 객체 형태는 `interface`, 유니온·교차는 `type` 사용.
- 함수 반환 타입은 명시한다 (추론에만 의존하지 않음).
- `null` 대신 `undefined` 우선 사용. DB 조회 결과 없음은 `null` 허용.

```typescript
// ✅ 올바른 예
interface Issue {
  id: number;
  title: string;
  assigneeId: number | undefined;
}

function getIssueById(id: number): Issue | undefined { ... }

// ❌ 금지
function getIssue(id: any): any { ... }
```

### 백엔드 Express 라우터 패턴

```typescript
// routes/issue-router.ts
import { Router, Request, Response, NextFunction } from 'express';
import { IssueService } from '../services/issue-service';

const router = Router();

router.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const issues = await IssueService.getAll(req.query);
    res.json({ data: issues });
  } catch (err) {
    next(err);  // 에러 미들웨어로 위임
  }
});

export default router;
```

### API 응답 형식

모든 API 응답은 아래 구조를 따른다.

```typescript
// 성공
{ "data": <payload> }

// 실패
{ "error": "<메시지>", "code": "<ERROR_CODE>" }
```

| HTTP 상태 | 용도 |
|----------|------|
| `200` | 조회·수정 성공 |
| `201` | 생성 성공 |
| `400` | 요청 형식 오류 (필수 필드 누락, 금지 전환 등) |
| `404` | 리소스 없음 |
| `500` | 서버 내부 오류 |

### 프론트엔드 컴포넌트 패턴

```typescript
// components/StatusBadge.tsx
interface StatusBadgeProps {
  status: 'TO DO' | 'DOING' | 'DONE' | 'PENDING';
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const styles = {
    'TO DO': 'bg-slate-100 text-slate-700',
    DOING:   'bg-blue-100 text-blue-700',
    DONE:    'bg-green-100 text-green-700',
    PENDING: 'bg-yellow-100 text-yellow-700',
  } as const;

  return (
    <span className={`rounded px-2 py-0.5 text-sm font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}
```

---

## 5. 테스트 규칙

- 기능 구현과 테스트는 같은 PR(또는 같은 커밋)에 포함한다. 테스트 없는 기능 완료 선언 금지.
- 백엔드 테스트는 인메모리 SQLite(`:memory:`)를 사용하여 실 DB와 격리한다.
- 테스트 파일명은 대상 파일명과 동일하게 `*.test.ts` / `*.test.tsx`.
- `describe` 블록으로 기능 단위를 묶고, `test` / `it` 으로 케이스를 나눈다.
- 테스트 설명은 한국어로 작성한다.

```typescript
// ✅ 올바른 예
describe('칸반 상태 전환', () => {
  test('TO DO → DOING 전환 성공', async () => { ... });
  test('금지된 전환 시도 시 400 반환', async () => { ... });
});

// ❌ 금지
test('test1', async () => { ... });
```

---

## 6. 보안 규칙

| 규칙 | 상세 |
|------|------|
| 시크릿 하드코딩 금지 | `GITHUB_TOKEN`, `JWT_SECRET` 등은 반드시 `process.env` 로만 참조 |
| GitHub Token 사용 위치 | 백엔드 `services/` 레이어에서만 사용. 라우터·프론트 직접 참조 금지 |
| `.env` 커밋 금지 | `.gitignore`에 `.env` 등록 여부를 PR 전 반드시 확인 |
| `data/*.db` 커밋 금지 | `.gitignore`에 `data/` 등록 |
| 레포지토리 쓰기 금지 | GitHub API 호출은 GET 메서드만 허용. POST·PATCH·DELETE 호출 코드 작성 금지 |
