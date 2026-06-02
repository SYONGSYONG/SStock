import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { SignalLog } from "../components/SignalLog";
import type { Signal } from "../types";

const sample: Signal[] = [
  {
    id: 1,
    symbol: "005930",
    strategy: "ma_cross",
    side: "BUY",
    price: 70000,
    reason: "골든크로스",
    created_at: "2026-06-03 09:05:00",
  },
];

describe("SignalLog", () => {
  test("신호가 없으면 안내 문구", () => {
    render(<SignalLog signals={[]} />);
    expect(screen.getByText(/아직 신호가 없습니다/)).toBeInTheDocument();
  });

  test("신호 행을 매수/매도로 표시", () => {
    render(<SignalLog signals={sample} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("매수")).toBeInTheDocument();
    expect(screen.getByText("골든크로스")).toBeInTheDocument();
  });
});
