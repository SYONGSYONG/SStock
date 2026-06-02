import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AccountPanel } from "../components/AccountPanel";
import type { AccountBalance } from "../types";

const balance: AccountBalance = {
  mode: "paper",
  available: true,
  deposit: 9500000,
  orderable_cash: 9480000,
  purchase_amount: 500000,
  eval_amount: 520000,
  eval_pnl: 20000,
  total_eval: 10000000,
  net_asset: 10000000,
};

describe("AccountPanel", () => {
  test("예수금/주문가능/총평가/평가손익을 표시", () => {
    render(<AccountPanel balance={balance} />);
    expect(screen.getByText("예수금")).toBeInTheDocument();
    expect(screen.getByText(/9,500,000/)).toBeInTheDocument(); // 예수금
    expect(screen.getByText(/9,480,000/)).toBeInTheDocument(); // 주문가능현금
    expect(screen.getByText("모의")).toBeInTheDocument();
  });

  test("평가손익이 양수면 + 부호로 표시", () => {
    render(<AccountPanel balance={balance} />);
    expect(screen.getByText(/\+20,000/)).toBeInTheDocument();
  });

  test("조회 불가(available=false)면 안내와 - 표시", () => {
    render(
      <AccountPanel
        balance={{ ...balance, available: false, deposit: null, orderable_cash: null }}
      />,
    );
    expect(screen.getByText("조회 불가")).toBeInTheDocument();
  });

  test("balance가 null이면 조회 불가 안내", () => {
    render(<AccountPanel balance={null} />);
    expect(screen.getByText("조회 불가")).toBeInTheDocument();
  });
});
