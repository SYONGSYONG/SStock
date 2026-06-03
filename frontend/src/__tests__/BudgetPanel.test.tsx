import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { BudgetPanel } from "../components/BudgetPanel";
import type { Budget } from "../types";

const budgets: Budget[] = [
  { symbol: "005930", principal: 500000, realized_pnl: 5000, holding_cost: 100000, ceiling: 505000, available: 405000 },
];

describe("BudgetPanel (요약)", () => {
  test("설정가능금액 = 주문가능현금 − 가용액 합계", () => {
    // 주문가능현금 1,000,000 − 가용액 405,000 = 설정가능 595,000
    render(<BudgetPanel budgets={budgets} orderableCash={1000000} />);
    expect(screen.getByText(/주문가능현금/)).toBeInTheDocument();
    expect(screen.getByText(/595,000/)).toBeInTheDocument();
    expect(screen.getByText(/설정된 칸막이 1종목/)).toBeInTheDocument();
  });

  test("주문가능현금 null이면 조회 불가 표기", () => {
    render(<BudgetPanel budgets={[]} orderableCash={null} />);
    expect(screen.getByText("주문가능현금 조회 불가")).toBeInTheDocument();
  });

  test("칸막이가 없으면 전략 추가 안내", () => {
    render(<BudgetPanel budgets={[]} orderableCash={1000000} />);
    expect(screen.getByText(/전략 추가 시 함께 등록됩니다/)).toBeInTheDocument();
  });

  test("종목별 목록을 더 이상 중복 표기하지 않는다", () => {
    render(<BudgetPanel budgets={budgets} orderableCash={1000000} />);
    // 종목 코드/가용·한도 상세는 전략 목록에서만 표기
    expect(screen.queryByText("005930")).toBeNull();
  });
});
