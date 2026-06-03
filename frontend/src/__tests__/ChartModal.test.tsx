import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { ChartModal } from "../components/ChartModal";
import type { ChartData, ChartInterval } from "../types";

vi.mock("lightweight-charts", () => {
  const series = {
    setData: vi.fn(),
    priceScale: () => ({ applyOptions: vi.fn() }),
  };
  const chart = {
    addSeries: vi.fn(() => series),
    timeScale: () => ({ fitContent: vi.fn() }),
    applyOptions: vi.fn(),
    remove: vi.fn(),
  };
  return {
    createChart: vi.fn(() => chart),
    CandlestickSeries: "Candlestick",
    HistogramSeries: "Histogram",
  };
});

const MAX_AUTO_RETRIES = 2;

const DAILY: ChartData = {
  symbol: "005930",
  interval: "daily",
  candles: [
    { time: "2026-06-01", open: 69000, high: 70000, low: 68800, close: 69800, volume: 9000000 },
    { time: "2026-06-02", open: 70000, high: 71000, low: 69500, close: 70500, volume: 12000000 },
  ],
};

afterEach(() => vi.clearAllMocks());

describe("ChartModal", () => {
  test("일봉/주봉/분봉 토글을 보여준다", async () => {
    const fetchChart = vi.fn().mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" name="삼성전자" fetchChart={fetchChart} onClose={() => {}} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "일봉" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "주봉" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "분봉" })).toBeInTheDocument();
    await waitFor(() => expect(fetchChart).toHaveBeenCalledWith("005930", "daily", expect.any(AbortSignal)));
  });

  test("주봉 탭을 누르면 weekly로 재조회한다", async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(() => expect(fetchChart).toHaveBeenCalledWith("005930", "daily", expect.any(AbortSignal)));
    fireEvent.click(screen.getByRole("tab", { name: "주봉" }));
    await waitFor(() => expect(fetchChart).toHaveBeenCalledWith("005930", "weekly", expect.any(AbortSignal)));
  });

  test("분봉 탭을 누르면 minute으로 재조회한다", async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(() => expect(fetchChart).toHaveBeenCalledWith("005930", "daily", expect.any(AbortSignal)));
    fireEvent.click(screen.getByRole("tab", { name: "분봉" }));
    await waitFor(() => expect(fetchChart).toHaveBeenCalledWith("005930", "minute", expect.any(AbortSignal)));
  });

  test("닫기 버튼 클릭 시 onClose를 호출한다", async () => {
    const onClose = vi.fn();
    const fetchChart = vi.fn().mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("닫기"));
    expect(onClose).toHaveBeenCalled();
  });

  test("Esc 키로 닫는다", async () => {
    const onClose = vi.fn();
    const fetchChart = vi.fn().mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  test("빈 캔들이면 데이터 없음 안내를 보여준다", async () => {
    const fetchChart = vi.fn().mockResolvedValue({ ...DAILY, candles: [] });
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(
      () => expect(screen.getByText("차트 데이터가 없습니다")).toBeInTheDocument(),
      { timeout: 4000 },
    );
    expect(fetchChart).toHaveBeenCalledTimes(1 + MAX_AUTO_RETRIES);
  });

  test("빈 캔들이면 자동 재시도 후 복구된 데이터를 보여준다", async () => {
    const fetchChart = vi
      .fn()
      .mockResolvedValueOnce({ ...DAILY, candles: [] })
      .mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(() => expect(fetchChart).toHaveBeenCalledTimes(2), { timeout: 2000 });
    expect(screen.queryByText("차트 데이터가 없습니다")).not.toBeInTheDocument();
    expect(screen.queryByText("차트 데이터를 불러올 수 없습니다")).not.toBeInTheDocument();
  });

  test("실패 후 자동 재시도로 복구한다", async () => {
    const fetchChart = vi
      .fn()
      .mockRejectedValueOnce(new Error("503"))
      .mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(() => expect(fetchChart).toHaveBeenCalledTimes(2), { timeout: 2000 });
    expect(screen.queryByText("차트 데이터를 불러올 수 없습니다")).not.toBeInTheDocument();
    expect(screen.queryByText("차트 데이터가 없습니다")).not.toBeInTheDocument();
  });

  test("연속 실패 시 오류 안내를 보여준다", async () => {
    const fetchChart = vi.fn().mockRejectedValue(new Error("fail"));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    await waitFor(
      () => expect(screen.getByText("차트 데이터를 불러올 수 없습니다")).toBeInTheDocument(),
      { timeout: 4000 },
    );
    expect(fetchChart).toHaveBeenCalledTimes(1 + MAX_AUTO_RETRIES);
  });
});
