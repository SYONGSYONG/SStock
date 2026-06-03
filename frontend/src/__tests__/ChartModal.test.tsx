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
    createSeriesMarkers: vi.fn(),
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
  test("기업개요/일봉/주봉/분봉 탭을 보여주고 일봉 클릭 시 차트를 조회한다", async () => {
    const fetchChart = vi.fn().mockResolvedValue(DAILY);
    render(<ChartModal symbol="005930" name="삼성전자" fetchChart={fetchChart} onClose={() => {}} />);
    expect(screen.getByText("005930")).toBeInTheDocument();
    expect(screen.getByText("삼성전자")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "기업개요" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "일봉" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "주봉" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "분봉" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "일봉" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "daily",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      ),
    );
  });

  test("기업개요 탭을 누르면 회사 개요를 보여준다", async () => {
    const fetchChart = vi.fn().mockResolvedValue(DAILY);
    const fetchOverview = vi.fn().mockResolvedValue({
      symbol: "005930",
      base_date: "2026.06.02",
      summary: ["1969년 설립된 글로벌 전자 기업", "DX/DS/SDC/Harman 부문 운영"],
      price: [{ label: "시가총액", value: "21,075,834억원" }],
      shareholders: [{ name: "삼성생명보험 외 15인", shares: "1,151,513,080", pct: "19.70" }],
      products: [{ name: "DS", pct: "61.04" }],
      history: [{ date: "2025/12", detail: "6세대 D램 양산" }],
    });
    render(
      <ChartModal
        symbol="005930"
        fetchChart={fetchChart}
        fetchOverview={fetchOverview}
        onClose={() => {}}
      />,
    );
    // 기업개요가 기본(첫) 탭이라 클릭 없이 표시된다
    expect(screen.getByRole("tab", { name: "기업개요" })).toBeInTheDocument();

    expect(await screen.findByText("1969년 설립된 글로벌 전자 기업")).toBeInTheDocument();
    expect(screen.getByText("기준: 2026.06.02")).toBeInTheDocument();
    // 시세·주주현황·매출구성·연혁 표
    expect(screen.getByText("시가총액")).toBeInTheDocument();
    expect(screen.getByText("삼성생명보험 외 15인")).toBeInTheDocument();
    expect(screen.getByText("19.70%")).toBeInTheDocument();
    expect(screen.getByText("주요제품 매출구성")).toBeInTheDocument();
    expect(screen.getByText("61.04%")).toBeInTheDocument();
    expect(screen.getByText("최근연혁")).toBeInTheDocument();
    expect(screen.getByText("6세대 D램 양산")).toBeInTheDocument();
    expect(fetchOverview).toHaveBeenCalledWith("005930");
  });

  test("주봉 탭을 누르면 weekly로 재조회한다", async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "주봉" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "weekly",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      ),
    );
  });

  test("분봉 탭을 누르면 minute으로 재조회한다", async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "분봉" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "minute",
        expect.objectContaining({ signal: expect.any(AbortSignal), unit: 1 }),
      ),
    );
  });

  test("분봉 단위(5분)를 누르면 unit=5로 재조회한다", async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "분봉" }));
    fireEvent.click(screen.getByRole("tab", { name: "5분" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "minute",
        expect.objectContaining({ unit: 5 }),
      ),
    );
  });

  test('당일분봉(minuteScope="today")일 때 단위 선택기를 렌더하지 않고 scope="today"로 호출한다', async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(
      <ChartModal
        symbol="005930"
        minuteScope="today"
        fetchChart={fetchChart}
        onClose={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: "분봉" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "minute",
        expect.objectContaining({ scope: "today", unit: 1 }),
      ),
    );
    // 당일분봉일 때는 단위 선택기가 렌더되지 않음
    expect(screen.queryByRole("tab", { name: "5분" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "10분" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "30분" })).not.toBeInTheDocument();
  });

  test('세션분봉(minuteScope="session", 기본)일 때 단위 선택기를 렌더하고 scope="session"로 호출한다', async () => {
    const fetchChart = vi
      .fn()
      .mockImplementation((_s: string, iv: ChartInterval) => Promise.resolve({ ...DAILY, interval: iv }));
    render(
      <ChartModal
        symbol="005930"
        minuteScope="session"
        fetchChart={fetchChart}
        onClose={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("tab", { name: "분봉" }));
    await waitFor(() =>
      expect(fetchChart).toHaveBeenCalledWith(
        "005930",
        "minute",
        expect.objectContaining({ scope: "session", unit: 1 }),
      ),
    );
    // 세션분봉일 때는 단위 선택기가 렌더됨
    expect(screen.getByRole("tab", { name: "5분" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "10분" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "30분" })).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("tab", { name: "일봉" }));
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
    fireEvent.click(screen.getByRole("tab", { name: "일봉" }));
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
    fireEvent.click(screen.getByRole("tab", { name: "일봉" }));
    await waitFor(() => expect(fetchChart).toHaveBeenCalledTimes(2), { timeout: 2000 });
    expect(screen.queryByText("차트 데이터를 불러올 수 없습니다")).not.toBeInTheDocument();
    expect(screen.queryByText("차트 데이터가 없습니다")).not.toBeInTheDocument();
  });

  test("연속 실패 시 오류 안내를 보여준다", async () => {
    const fetchChart = vi.fn().mockRejectedValue(new Error("fail"));
    render(<ChartModal symbol="005930" fetchChart={fetchChart} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: "일봉" }));
    await waitFor(
      () => expect(screen.getByText("차트 데이터를 불러올 수 없습니다")).toBeInTheDocument(),
      { timeout: 4000 },
    );
    expect(fetchChart).toHaveBeenCalledTimes(1 + MAX_AUTO_RETRIES);
  });
});
