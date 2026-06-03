import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { QuoteTable } from "../components/QuoteTable";
import type { WatchItem } from "../types";

const items: WatchItem[] = [
  { id: 1, symbol: "005930", name: "삼성전자", created_at: "" },
  { id: 2, symbol: "000660", name: "SK하이닉스", created_at: "" },
];

describe("QuoteTable", () => {
  test("종목코드 클릭 시 onPickSymbol(symbol)이 호출된다", () => {
    const onPickSymbol = vi.fn();
    render(
      <QuoteTable items={items} quotes={{}} strategySymbols={new Set()} onPickSymbol={onPickSymbol} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /005930/ }));
    expect(onPickSymbol).toHaveBeenCalledWith("005930");
  });

  test("전략 등록 종목은 행이 강조된다(with-strategy)", () => {
    render(
      <QuoteTable
        items={items}
        quotes={{}}
        strategySymbols={new Set(["000660"])}
        onPickSymbol={() => {}}
      />,
    );
    const row = screen.getByText("SK하이닉스").closest("tr") as HTMLElement;
    expect(row.className).toContain("with-strategy");
  });
});
