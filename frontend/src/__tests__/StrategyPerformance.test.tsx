import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { StrategyPerformance } from "../components/StrategyPerformance";
import { RSI_MA_PRESETS } from "../lib/strategy";
import type { Quote, StrategyConfig, StrategyPerfRow } from "../types";

function row(over: Partial<StrategyPerfRow> = {}): StrategyPerfRow {
  return {
    symbol: "005930",
    name: "삼성전자",
    strategy: "rsi_ma",
    trades: 8,
    wins: 5,
    win_rate: 62.5,
    sum_return: 10,
    avg_return: 1.25,
    open_position: 0,
    open_entry: null,
    ...over,
  };
}

function quote(symbol: string, price: number): Record<string, Quote> {
  return {
    [symbol]: { symbol, price, change: null, change_rate: null, sign: null, volume: null },
  };
}

function renderBoard(rows: StrategyPerfRow[], opts: Partial<{
  configs: StrategyConfig[];
  quotes: Record<string, Quote>;
  onPeriodChange: (p: "all" | "today" | "3d" | "7d") => void;
}> = {}) {
  return render(
    <StrategyPerformance
      rows={rows}
      configs={opts.configs ?? []}
      quotes={opts.quotes ?? {}}
      period="all"
      onPeriodChange={opts.onPeriodChange ?? (() => {})}
    />,
  );
}

describe("StrategyPerformance", () => {
  test("행이 없으면 안내 문구를 보여준다", () => {
    renderBoard([]);
    expect(screen.getByText(/아직 완결된 가상 거래가 없습니다/)).toBeInTheDocument();
  });

  test("종목·전략·승률·누적수익률을 표시한다", () => {
    renderBoard([row()]);
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByText("RSI + MA 필터")).toBeInTheDocument();
    expect(screen.getByText("+10.00%")).toBeInTheDocument(); // 누적
    expect(screen.getByText("63%")).toBeInTheDocument(); // 승률 반올림
  });

  test("손실은 음수 부호로 표시한다", () => {
    renderBoard([row({ sum_return: -7.5, avg_return: -7.5 })]);
    expect(screen.getAllByText("-7.50%").length).toBeGreaterThan(0);
  });

  test("완결 거래가 0이면 수익률을 대시로 표시한다", () => {
    renderBoard([row({ trades: 0, wins: 0, win_rate: 0, sum_return: 0, avg_return: 0 })]);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  test("현재 설정이 프리셋과 일치하면 프리셋 배지를 병기한다", () => {
    const preset = RSI_MA_PRESETS[0];
    const cfg: StrategyConfig = {
      id: 1,
      symbol: "005930",
      strategy: "rsi_ma",
      params: { ...preset.params },
      enabled: true,
      max_qty: null,
      max_amount: null,
    };
    renderBoard([row()], { configs: [cfg] });
    expect(screen.getByText(preset.label)).toBeInTheDocument();
  });

  test("완결 거래가 적으면(표본 부족) 경고 칩을 표시한다", () => {
    renderBoard([row({ trades: 2, wins: 1, win_rate: 50 })]);
    expect(screen.getByText("표본 부족")).toBeInTheDocument();
  });

  test("표본이 충분하면 경고 칩이 없다", () => {
    renderBoard([row({ trades: 8 })]);
    expect(screen.queryByText("표본 부족")).not.toBeInTheDocument();
  });

  test("미청산 + 현재가가 있으면 미실현 수익률을 계산한다", () => {
    // 진입 1000, 현재가 1075 → +7.50%(누적값과 겹치지 않게 분리)
    renderBoard([row({ sum_return: 3.33, avg_return: 0.42, open_position: 1, open_entry: 1000 })], {
      quotes: quote("005930", 1075),
    });
    expect(screen.getByText("+7.50%")).toBeInTheDocument();
  });

  test("미청산이지만 현재가가 없으면 '보유'로 표시한다", () => {
    renderBoard([row({ open_position: 1, open_entry: 1000 })], { quotes: {} });
    expect(screen.getByText("보유")).toBeInTheDocument();
  });

  test("기간 버튼 클릭 시 onPeriodChange를 호출한다", () => {
    const onPeriodChange = vi.fn();
    renderBoard([row()], { onPeriodChange });
    fireEvent.click(screen.getByRole("button", { name: "최근 7일" }));
    expect(onPeriodChange).toHaveBeenCalledWith("7d");
  });
});
