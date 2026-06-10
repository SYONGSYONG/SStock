import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AuditLogView } from "../components/AuditLogView";
import type { AuditLog } from "../types";

// 백엔드 /api/audit는 최신순(DESC, id 내림차순)으로 내려준다 — 테스트도 동일 순서로
// 둬서 컷오프가 배열 위치가 아닌 created_at 최댓값 기준으로 동작하는지 검증한다.
const sampleLogs: AuditLog[] = [
  {
    id: 3,
    category: "SIGNAL",
    message: "신호 발생",
    created_at: "2026-06-04 10:00:00",
  },
  {
    id: 2,
    category: "ORDER",
    message: "매수 주문 체결",
    created_at: "2026-06-03 09:10:00",
  },
  {
    id: 1,
    category: "BOT",
    message: "봇이 시작됨",
    created_at: "2026-06-03 09:05:00",
  },
];

describe("AuditLogView", () => {
  test("로그가 없으면 안내 문구", () => {
    render(<AuditLogView logs={[]} />);
    expect(screen.getByText(/로그가 없습니다/)).toBeInTheDocument();
  });

  test("로그 행들이 표시됨", () => {
    render(<AuditLogView logs={sampleLogs} />);
    expect(screen.getByText("봇이 시작됨")).toBeInTheDocument();
    expect(screen.getByText("매수 주문 체결")).toBeInTheDocument();
  });

  test("로그의 일시가 MM-DD HH:MM:SS 형태로 표시", () => {
    render(<AuditLogView logs={sampleLogs} />);
    expect(screen.getByText("06-03 09:05:00")).toBeInTheDocument();
    expect(screen.getByText("06-04 10:00:00")).toBeInTheDocument();
  });

  test("지우기 버튼이 존재", () => {
    render(<AuditLogView logs={sampleLogs} />);
    const clearButton = screen.getByRole("button", { name: /지우기|초기화|clear/i });
    expect(clearButton).toBeInTheDocument();
  });

  test("지우기 버튼을 누르면 현재 보이는 로그가 사라짐", () => {
    const { rerender } = render(<AuditLogView logs={sampleLogs} />);
    const clearButton = screen.getByRole("button");
    fireEvent.click(clearButton);

    // clear 후 다시 렌더링
    rerender(<AuditLogView logs={sampleLogs} />);

    // 기존 로그들이 보이지 않아야 함
    expect(screen.queryByText("봇이 시작됨")).not.toBeInTheDocument();
    expect(screen.queryByText("매수 주문 체결")).not.toBeInTheDocument();
    expect(screen.getByText(/로그가 없습니다/)).toBeInTheDocument();
  });

  test("clear 후 새로운 로그만 표시됨(클라이언트 컷오프)", () => {
    const { rerender } = render(<AuditLogView logs={sampleLogs} />);
    const clearButton = screen.getByRole("button");
    fireEvent.click(clearButton);

    // 새 로그가 맨 앞(최신순) + 기존 로그
    const newLogs: AuditLog[] = [
      {
        id: 4,
        category: "ERROR",
        message: "에러 발생",
        created_at: "2026-06-04 11:00:00",
      },
      sampleLogs[0],
      sampleLogs[1],
      sampleLogs[2],
    ];

    rerender(<AuditLogView logs={newLogs} />);

    // 새 로그만 표시
    expect(screen.queryByText("봇이 시작됨")).not.toBeInTheDocument();
    expect(screen.getByText("에러 발생")).toBeInTheDocument();
  });
});
