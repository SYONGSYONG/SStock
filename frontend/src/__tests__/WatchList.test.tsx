import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { WatchList } from "../components/WatchList";
import type { StockSearchResult } from "../types";

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

describe("WatchList 키보드 조작", () => {
  test("엔터만 누르면 첫 결과 선택", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005930", "삼성전자");
  });

  test("화살표 아래로 이동 후 엔터로 두 번째 결과 선택", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005935", "삼성전자우");
  });

  test("화살표 위로 순환(첫 항목에서 위 → 마지막)", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "ArrowUp" }); // 0 -> 마지막(1)
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).toHaveBeenCalledWith("005935", "삼성전자우");
  });

  test("Esc로 닫으면 엔터해도 선택 안 됨", async () => {
    const { onAdd, input } = setup();
    fireEvent.change(input, { target: { value: "삼성" } });
    await screen.findByText("삼성전자우");

    fireEvent.keyDown(input, { key: "Escape" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onAdd).not.toHaveBeenCalled();
  });
});
