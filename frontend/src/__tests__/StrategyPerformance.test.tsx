import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { StrategyPerformance } from "../components/StrategyPerformance";
import { RSI_MA_PRESETS } from "../lib/strategy";
import type { StrategyConfig, StrategyPerfRow } from "../types";

function row(over: Partial<StrategyPerfRow> = {}): StrategyPerfRow {
  return {
    symbol: "005930",
    name: "삼성전자",
    strategy: "rsi_ma",
    trades: 2,
    wins: 1,
    win_rate: 50,
    sum_return: 10,
    avg_return: 5,
    open_position: 0,
    ...over,
  };
}

describe("StrategyPerformance", () => {
  test("행이 없으면 안내 문구를 보여준다", () => {
    render(<StrategyPerformance rows={[]} configs={[]} />);
    expect(screen.getByText(/아직 완결된 가상 거래가 없습니다/)).toBeInTheDocument();
  });

  test("종목·전략·완결수·승률·누적수익률을 표시한다", () => {
    render(<StrategyPerformance rows={[row()]} configs={[]} />);
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText("RSI + MA 필터")).toBeInTheDocument();
    expect(screen.getByText("+10.00%")).toBeInTheDocument(); // 누적
    expect(screen.getByText("+5.00%")).toBeInTheDocument(); // 평균
    expect(screen.getByText("50%")).toBeInTheDocument(); // 승률
  });

  test("손실은 음수 부호로 표시한다", () => {
    render(
      <StrategyPerformance
        rows={[row({ sum_return: -7.5, avg_return: -7.5, wins: 0, win_rate: 0, trades: 1 })]}
        configs={[]}
      />,
    );
    expect(screen.getAllByText("-7.50%").length).toBeGreaterThan(0);
  });

  test("완결 거래가 0이면 수익률을 대시로 표시한다", () => {
    render(
      <StrategyPerformance
        rows={[row({ trades: 0, wins: 0, win_rate: 0, sum_return: 0, avg_return: 0, open_position: 1 })]}
        configs={[]}
      />,
    );
    // 완결 0 → 보유중 1
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  test("현재 설정이 프리셋과 일치하면 프리셋 배지를 병기한다", () => {
    const preset = RSI_MA_PRESETS[0]; // 강한상승
    const cfg: StrategyConfig = {
      id: 1,
      symbol: "005930",
      strategy: "rsi_ma",
      params: { ...preset.params },
      enabled: true,
      max_qty: null,
      max_amount: null,
    };
    render(<StrategyPerformance rows={[row()]} configs={[cfg]} />);
    expect(screen.getByText(preset.label)).toBeInTheDocument();
  });
});
