import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { BudgetPanel } from "../components/BudgetPanel";
import type { Budget, WatchItem } from "../types";

const items: WatchItem[] = [
  { id: 1, symbol: "005930", name: "삼성전자", created_at: "" },
];

const budgets: Budget[] = [
  { symbol: "005930", principal: 500000, realized_pnl: 5000, holding_cost: 100000, ceiling: 505000, available: 405000 },
];

describe("BudgetPanel", () => {
  test("칸막이 현황을 가용/한도로 표시", () => {
    render(<BudgetPanel budgets={budgets} items={items} onSet={() => {}} onRemove={() => {}} />);
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText(/405,000/)).toBeInTheDocument(); // 가용
    expect(screen.getByText(/505,000원/)).toBeInTheDocument(); // 한도
  });

  test("종목코드+원금 입력 후 설정 호출", () => {
    const onSet = vi.fn();
    render(<BudgetPanel budgets={[]} items={[]} onSet={onSet} onRemove={() => {}} />);
    fireEvent.change(screen.getByLabelText("칸막이 종목코드"), { target: { value: "000660" } });
    fireEvent.change(screen.getByLabelText("원금"), { target: { value: "300000" } });
    fireEvent.click(screen.getByText("설정"));
    expect(onSet).toHaveBeenCalledWith("000660", 300000);
  });

  test("빈 칸막이 안내", () => {
    render(<BudgetPanel budgets={[]} items={[]} onSet={() => {}} onRemove={() => {}} />);
    expect(screen.getByText(/설정된 칸막이가 없습니다/)).toBeInTheDocument();
  });
});
