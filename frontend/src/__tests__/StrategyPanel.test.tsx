import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { StrategyPanel, describeStrategy } from "../components/StrategyPanel";
import type { StrategyConfig } from "../types";

describe("describeStrategy", () => {
  test("이동평균 크로스는 단기/장기로 표기", () => {
    expect(describeStrategy("ma_cross", { short: 5, long: 20 })).toBe(
      "이동평균 크로스 · 단기 5 / 장기 20",
    );
  });

  test("RSI는 기간/과매도/과매수로 표기", () => {
    expect(describeStrategy("rsi", { period: 14, low: 30, high: 70 })).toBe(
      "RSI · 기간 14 · 과매도 30 / 과매수 70",
    );
  });
});

describe("StrategyPanel", () => {
  test("원시 JSON이 아니라 한글 라벨로 렌더링", () => {
    const configs: StrategyConfig[] = [
      { id: 1, symbol: "077360", strategy: "ma_cross", params: { short: 5, long: 20 }, enabled: true, max_qty: 10, max_amount: null },
    ];
    render(
      <StrategyPanel
        configs={configs}
        onAdd={() => {}}
        onToggle={() => {}}
        onRemove={() => {}}
      />,
    );
    expect(screen.getByText("이동평균 크로스 · 단기 5 / 장기 20")).toBeInTheDocument();
    expect(screen.queryByText(/\{"short"/)).toBeNull();
  });
});
