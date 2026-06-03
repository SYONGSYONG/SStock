import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
  type IChartApi,
} from "lightweight-charts";
import type { ChartData, ChartInterval } from "../types";

interface ChartModalProps {
  symbol: string;
  name?: string | null;
  fetchChart: (symbol: string, interval: ChartInterval, signal?: AbortSignal) => Promise<ChartData>;
  onClose: () => void;
}

const UP = "#d12e2e";
const DOWN = "#1f5fd1";

const AUTO_RETRY_DELAY_MS = 700;
const MAX_AUTO_RETRIES = 2;

/** 종목 캔들차트 모달(일봉/주봉/분봉 토글, lightweight-charts). */
export function ChartModal({ symbol, name, fetchChart, onClose }: ChartModalProps) {
  const [interval, setIntervalState] = useState<ChartInterval>("daily");
  const [candles, setCandles] = useState<ChartData["candles"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const autoRetriesRef = useRef(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    autoRetriesRef.current = 0;
  }, [symbol, interval]);

  useEffect(() => {
    let alive = true;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const scheduleRetry = (): boolean => {
      if (autoRetriesRef.current >= MAX_AUTO_RETRIES) return false;
      autoRetriesRef.current += 1;
      const delay = AUTO_RETRY_DELAY_MS * autoRetriesRef.current;
      retryTimer = setTimeout(() => {
        if (alive) setRetryCount((c) => c + 1);
      }, delay);
      return true;
    };

    fetchChart(symbol, interval, controller.signal)
      .then((d) => {
        if (!alive) return;
        if (d.candles.length === 0 && scheduleRetry()) return;
        setCandles(d.candles);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        if (scheduleRetry()) return;
        setError("차트 데이터를 불러올 수 없습니다");
        setLoading(false);
      });

    return () => {
      alive = false;
      if (retryTimer) clearTimeout(retryTimer);
      controller.abort();
    };
  }, [symbol, interval, fetchChart, retryCount]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || candles.length === 0) return;

    const chart: IChartApi = createChart(el, {
      width: el.clientWidth,
      height: el.clientHeight,
      layout: { background: { color: "#ffffff" }, textColor: "#1b1f24" },
      grid: { vertLines: { color: "#eef1f4" }, horzLines: { color: "#eef1f4" } },
      timeScale: { timeVisible: interval === "minute", borderColor: "#e3e6ea" },
      rightPriceScale: { borderColor: "#e3e6ea" },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP,
      downColor: DOWN,
      borderUpColor: UP,
      borderDownColor: DOWN,
      wickUpColor: UP,
      wickDownColor: DOWN,
    });
    candleSeries.setData(
      candles.map((c) => ({
        time: c.time as never,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time as never,
        value: c.volume,
        color: c.close >= c.open ? "#f3c1c1" : "#c1cdf0",
      })),
    );

    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [candles, interval]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal chart-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${symbol} 차트`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="chart-modal-head">
          <h2>
            <span className="code">{symbol}</span> {name ?? ""}
          </h2>
          <div className="chart-toggle" role="tablist" aria-label="차트 주기">
            <button
              role="tab"
              aria-selected={interval === "daily"}
              className={interval === "daily" ? "active" : ""}
              onClick={() => setIntervalState("daily")}
            >
              일봉
            </button>
            <button
              role="tab"
              aria-selected={interval === "weekly"}
              className={interval === "weekly" ? "active" : ""}
              onClick={() => setIntervalState("weekly")}
            >
              주봉
            </button>
            <button
              role="tab"
              aria-selected={interval === "minute"}
              className={interval === "minute" ? "active" : ""}
              onClick={() => setIntervalState("minute")}
            >
              분봉
            </button>
          </div>
          <button className="modal-close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </header>

        <div className="chart-body">
          <div ref={containerRef} className="chart-canvas" />
          {loading && <p className="chart-overlay muted">불러오는 중...</p>}
          {error && (
            <div className="chart-overlay error">
              <p>{error}</p>
              <button onClick={() => setRetryCount((c) => c + 1)}>다시 시도</button>
            </div>
          )}
          {!loading && !error && candles.length === 0 && (
            <div className="chart-overlay empty">
              <p>차트 데이터가 없습니다</p>
              <button onClick={() => setRetryCount((c) => c + 1)}>다시 시도</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
