import { fireEvent, render, screen, within } from "@testing-library/react";
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

  test("설정가능금액 = 주문가능현금 − 가용액 합계", () => {
    // 주문가능현금 1,000,000 − 가용액 405,000 = 설정가능 595,000
    render(
      <BudgetPanel
        budgets={budgets}
        items={items}
        onSet={() => {}}
        onRemove={() => {}}
        orderableCash={1000000}
      />,
    );
    expect(screen.getByText(/주문가능현금/)).toBeInTheDocument();
    expect(screen.getByText(/595,000/)).toBeInTheDocument();
  });

  test("주문가능현금 null이면 조회 불가 표기", () => {
    render(
      <BudgetPanel budgets={[]} items={[]} onSet={() => {}} onRemove={() => {}} orderableCash={null} />,
    );
    expect(screen.getByText("주문가능현금 조회 불가")).toBeInTheDocument();
  });

  test("설정가능금액 초과 입력 시 경고만 표시(설정 버튼 활성)", () => {
    render(
      <BudgetPanel
        budgets={[]}
        items={[]}
        onSet={() => {}}
        onRemove={() => {}}
        orderableCash={100000}
      />,
    );
    fireEvent.change(screen.getByLabelText("칸막이 종목코드"), { target: { value: "000660" } });
    fireEvent.change(screen.getByLabelText("원금"), { target: { value: "300000" } });
    expect(screen.getByText(/설정가능금액.*초과/)).toBeInTheDocument();
    expect(screen.getByText("설정")).not.toBeDisabled(); // 차단 안 함
  });

  test("수정 버튼 → 모달에서 원금을 고쳐 저장하면 onSet 호출", () => {
    const onSet = vi.fn();
    render(<BudgetPanel budgets={budgets} items={items} onSet={onSet} onRemove={() => {}} />);
    expect(screen.queryByRole("dialog")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "수정" }));
    const dialog = screen.getByRole("dialog");
    // 현재 원금이 채워져 있다
    expect((within(dialog).getByLabelText("수정 원금") as HTMLInputElement).value).toBe("500000");

    fireEvent.change(within(dialog).getByLabelText("수정 원금"), { target: { value: "700000" } });
    fireEvent.click(within(dialog).getByText("저장"));

    expect(onSet).toHaveBeenCalledWith("005930", 700000);
    expect(screen.queryByRole("dialog")).toBeNull(); // 저장 후 닫힘
  });
});
