import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { WatchList } from "../components/WatchList";
import type { StockSearchResult, WatchItem } from "../types";

const RESULTS: StockSearchResult[] = [
  { symbol: "005930", name: "삼성전자" },
  { symbol: "005935", name: "삼성전자우" },
];

function setup() {
  const onAdd = vi.fn();
  const search = vi.fn(async () => RESULTS);
  render(<WatchList items={[]} onAdd={onAdd} onRemove={() => {}} search={search} />);
  return { onAdd, search, input: screen.getByLabelText("종목 검색") };
}

describe("WatchList 검색", () => {
  test("엔터로 첫 결과를 선택한다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005930", "삼성전자");
  });

  test("아래 화살표로 두 번째 결과를 선택한다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005935", "삼성전자우");
  });

  test("아래에서 위로 순환한다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "ArrowUp" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005935", "삼성전자우");
  });

  test("Escape로 닫으면 선택되지 않는다", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "Escape" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).not.toHaveBeenCalled();
  });
});

describe("WatchList 종목 열기", () => {
  const items: WatchItem[] = [{ id: 1, symbol: "005930", name: "삼성전자", created_at: "" }];

  test("종목 클릭 시 onSelect(symbol, name)을 호출한다", () => {
    const onSelect = vi.fn();
    render(
      <WatchList
        items={items}
        onAdd={() => {}}
        onRemove={() => {}}
        onSelect={onSelect}
        search={vi.fn(async () => [])}
      />,
    );
    fireEvent.click(screen.getByTitle("차트 보기"));
    expect(onSelect).toHaveBeenCalledWith("005930", "삼성전자");
  });

  test("삭제 버튼은 onSelect를 호출하지 않는다", () => {
    const onSelect = vi.fn();
    const onRemove = vi.fn();
    render(
      <WatchList
        items={items}
        onAdd={() => {}}
        onRemove={onRemove}
        onSelect={onSelect}
        search={vi.fn(async () => [])}
      />,
    );
    fireEvent.click(screen.getByText("삭제"));
    expect(onRemove).toHaveBeenCalledWith("005930");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
