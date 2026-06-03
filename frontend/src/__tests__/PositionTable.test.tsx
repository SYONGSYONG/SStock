import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { PositionTable } from "../components/PositionTable";
import type { Position, Quote } from "../types";

const positions: Position[] = [
  {
    symbol: "005930",
    name: "삼성전자",
    qty: 10,
    avg_price: 68000,
    price: 70000,
    eval_amount: 700000,
    pl_amount: 20000,
    pl_rate: 2.94,
  },
];

const quotes: Record<string, Quote> = {
  "005930": {
    symbol: "005930",
    price: 70500,
    change: 500,
    change_rate: 0.71,
    sign: "+",
    volume: 1000,
  },
};

describe("PositionTable", () => {
  test("평단/현재가/평가금액/손익/손익률을 보여준다", () => {
    render(<PositionTable positions={positions} quotes={quotes} />);

    expect(screen.getByText("보유 포지션")).toBeInTheDocument();
    expect(screen.getByText("68,000")).toBeInTheDocument();
    expect(screen.getByText("70,500")).toBeInTheDocument();
    expect(screen.getByText("700,000")).toBeInTheDocument();
    expect(screen.getByText("20,000")).toBeInTheDocument();
    expect(screen.getByText("+2.94%")).toBeInTheDocument();
  });

  test("보유가 없으면 빈 상태를 보여준다", () => {
    render(<PositionTable positions={[]} quotes={{}} />);
    expect(screen.getByText("보유 포지션이 없습니다")).toBeInTheDocument();
  });
});
