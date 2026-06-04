import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { TradePnlPage } from "../components/TradePnlPage";
import type { TradePnlResult } from "../types";

const RESULT: TradePnlResult = {
  rows: [
    {
      trade_date: "2026-06-04",
      symbol: "005930",
      name: "삼성전자",
      source: "bot",
      sell_qty: 10,
      buy_unit_price: 1000,
      sell_unit_price: 1500,
      buy_amount: 10000,
      sell_amount: 15000,
      buy_fee: 2,
      sell_fee: 2,
      fee: 4,
      tax: 23,
      realized_pnl: 4973,
      pnl_rate: 49.73,
    },
  ],
  summary: {
    sell: { qty: 10, amount: 15000, fee: 2, tax: 23, settle: 14975 },
    buy: { qty: 10, amount: 10000, fee: 2, tax: 0, settle: 10002 },
    realized_pnl_total: 4973,
    total_pnl_rate: 49.73,
  },
  source: "local",
  estimated: true,
  available: true,
  period: { start: "2026-06-04", end: "2026-06-04" },
};

describe("TradePnlPage", () => {
  test("마운트 시 조회하고 행·요약·추정 안내를 표시", async () => {
    const fetchTradePnl = vi.fn().mockResolvedValue(RESULT);
    render(<TradePnlPage mode="paper" fetchTradePnl={fetchTradePnl} />);

    await waitFor(() => expect(fetchTradePnl).toHaveBeenCalled());
    expect(await screen.findByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText("4,973")).toBeInTheDocument(); // 실현손익(행)
    expect(screen.getByText(/추정치/)).toBeInTheDocument();
    expect(screen.getByText(/실현손익 합계/)).toBeInTheDocument();
  });

  test("조회 버튼은 현재 기간·정렬로 다시 조회", async () => {
    const fetchTradePnl = vi.fn().mockResolvedValue(RESULT);
    render(<TradePnlPage mode="paper" fetchTradePnl={fetchTradePnl} />);
    await waitFor(() => expect(fetchTradePnl).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByText("정순"));
    fireEvent.click(screen.getByText("조회"));
    await waitFor(() => expect(fetchTradePnl).toHaveBeenCalledTimes(2));
    const lastCall = fetchTradePnl.mock.calls.at(-1);
    expect(lastCall?.[0]).toBe("paper");
    expect(lastCall?.[1]).toMatchObject({ sort: "asc" });
  });

  test("데이터 없으면 안내 문구", async () => {
    const empty: TradePnlResult = {
      ...RESULT,
      rows: [],
      summary: { ...RESULT.summary, realized_pnl_total: 0 },
    };
    const fetchTradePnl = vi.fn().mockResolvedValue(empty);
    render(<TradePnlPage mode="paper" fetchTradePnl={fetchTradePnl} />);
    expect(await screen.findByText(/매매손익이 없습니다/)).toBeInTheDocument();
  });
});
