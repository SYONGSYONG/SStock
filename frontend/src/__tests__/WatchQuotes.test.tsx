import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { WatchQuotes } from "../components/WatchQuotes";
import type { StockSearchResult, WatchItem } from "../types";

const RESULTS: StockSearchResult[] = [
  { symbol: "005930", name: "삼성전자" },
  { symbol: "005935", name: "삼성전자우" },
];

const items: WatchItem[] = [
  { id: 1, symbol: "005930", name: "삼성전자", created_at: "" },
  { id: 2, symbol: "000660", name: "SK하이닉스", created_at: "" },
];

function base(overrides = {}) {
  return {
    items,
    quotes: {},
    strategySymbols: new Set<string>(),
    onAdd: () => {},
    onRemove: () => {},
    onSelect: () => {},
    onPickSymbol: () => {},
    search: vi.fn(async () => []),
    ...overrides,
  };
}

describe("WatchQuotes 검색(헤더 우측)", () => {
  function setup() {
    const onAdd = vi.fn();
    const search = vi.fn(async () => RESULTS);
    render(<WatchQuotes {...base({ items: [], onAdd, search })} />);
    return { onAdd, input: screen.getByLabelText("종목 검색") };
  }

  test("엔터로 첫 결과를 추가한다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005930", "삼성전자");
  });

  test("아래 화살표로 두 번째 결과를 추가한다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005935", "삼성전자우");
  });

  test("Escape로 닫으면 추가되지 않는다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");
    fireEvent.keyDown(input, { key: "Escape" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).not.toHaveBeenCalled();
  });
});

describe("WatchQuotes 행 동작", () => {
  test("전략이동 버튼 → onPickSymbol(symbol)", () => {
    const onPickSymbol = vi.fn();
    render(<WatchQuotes {...base({ onPickSymbol })} />);
    const row = screen.getByText("삼성전자").closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByRole("button", { name: "전략이동" }));
    expect(onPickSymbol).toHaveBeenCalledWith("005930");
  });

  test("종목명 클릭 → onSelect(symbol, name) (차트)", () => {
    const onSelect = vi.fn();
    render(<WatchQuotes {...base({ onSelect })} />);
    const row = screen.getByText("삼성전자").closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByTitle("차트 보기"));
    expect(onSelect).toHaveBeenCalledWith("005930", "삼성전자");
  });

  test("삭제 버튼 → onRemove, onSelect는 호출 안 함", () => {
    const onRemove = vi.fn();
    const onSelect = vi.fn();
    render(<WatchQuotes {...base({ onRemove, onSelect })} />);
    const row = screen.getByText("SK하이닉스").closest("tr") as HTMLElement;
    fireEvent.click(within(row).getByText("삭제"));
    expect(onRemove).toHaveBeenCalledWith("000660");
    expect(onSelect).not.toHaveBeenCalled();
  });

  test("전략 등록 종목은 행이 강조된다(with-strategy)", () => {
    render(<WatchQuotes {...base({ strategySymbols: new Set(["000660"]) })} />);
    const row = screen.getByText("SK하이닉스").closest("tr") as HTMLElement;
    expect(row.className).toContain("with-strategy");
  });

  test("종목이 없으면 안내 문구", () => {
    render(<WatchQuotes {...base({ items: [] })} />);
    expect(screen.getByText(/종목을 검색해 추가하세요/)).toBeInTheDocument();
  });
});
