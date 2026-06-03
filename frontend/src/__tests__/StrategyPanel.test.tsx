import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { StrategyPanel } from "../components/StrategyPanel";
import { describeStrategy } from "../lib/strategy";
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

  test("도움말 버튼을 누르면 중앙 모달로 전략 설명·5/20 의미가 뜬다", () => {
    render(
      <StrategyPanel configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} />,
    );
    // 닫힌 상태에서는 모달이 없다
    expect(screen.queryByRole("dialog")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "이동평균 크로스 도움말" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("골든크로스");
    expect(dialog).toHaveTextContent("시세(틱) 단위");
    // 설정값(5/20)의 의미 설명
    expect(dialog).toHaveTextContent("단기 5 = 최근 5개");
    expect(dialog).toHaveTextContent("장기 20 = 최근 20개");
  });

  test("배경 클릭으로 도움말 모달이 닫힌다", () => {
    render(
      <StrategyPanel configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "이동평균 크로스 도움말" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // 배경(닫기) 클릭
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("RSI 선택 시 도움말도 RSI 설명·14/30/70 의미로 바뀐다", () => {
    render(
      <StrategyPanel configs={[]} onAdd={() => {}} onToggle={() => {}} onRemove={() => {}} />,
    );
    fireEvent.change(screen.getByLabelText("전략 선택"), { target: { value: "rsi" } });
    fireEvent.click(screen.getByRole("button", { name: "RSI 도움말" }));

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("상대강도지수");
    expect(dialog).toHaveTextContent("기간 14 = 최근 14개");
    expect(dialog).toHaveTextContent("과매도 30");
    expect(dialog).toHaveTextContent("과매수 70");
  });
});
