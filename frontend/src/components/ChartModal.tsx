import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
  type IChartApi,
} from "lightweight-charts";
import type { ChartData, ChartInterval, CompanyOverview, MinuteUnit } from "../types";

type ChartTab = ChartInterval | "overview";

interface ChartModalProps {
  symbol: string;
  name?: string | null;
  minuteScope?: "today" | "session";
  fetchChart: (
    symbol: string,
    interval: ChartInterval,
    opts?: { unit?: number; scope?: "today" | "session"; signal?: AbortSignal },
  ) => Promise<ChartData>;
  fetchOverview?: (symbol: string) => Promise<CompanyOverview>;
  onClose: () => void;
}

const UP = "#d12e2e";
const DOWN = "#1f5fd1";

const AUTO_RETRY_DELAY_MS = 700;
const MAX_AUTO_RETRIES = 2;

const MINUTE_UNITS: MinuteUnit[] = [1, 5, 10, 30];

/** 종목 모달: 캔들차트(일봉/주봉/분봉) + 기업개요 탭. */
export function ChartModal({ symbol, name, minuteScope = "session", fetchChart, fetchOverview, onClose }: ChartModalProps) {
  const [tab, setTab] = useState<ChartTab>("overview");
  const [candles, setCandles] = useState<ChartData["candles"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const autoRetriesRef = useRef(0);
  // 이미 받은 캔들을 (interval+분단위)별로 메모 → 다시 눌러도 재조회하지 않는다.
  const candlesCacheRef = useRef<Map<string, ChartData["candles"]>>(new Map());
  // 분봉 단위(1·5·10·30분)
  const [minuteUnit, setMinuteUnit] = useState<MinuteUnit>(1);

  // 기업개요
  const [overview, setOverview] = useState<CompanyOverview | null>(null);
  const [ovLoading, setOvLoading] = useState(false);
  const [ovError, setOvError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    autoRetriesRef.current = 0;
  }, [symbol, tab, minuteUnit, minuteScope]);

  // 종목이 바뀌면 메모를 비운다(이전 종목 캔들 재사용 방지).
  useEffect(() => {
    candlesCacheRef.current.clear();
  }, [symbol]);

  // 차트 데이터 조회 (차트 탭일 때만)
  useEffect(() => {
    if (tab === "overview") return;
    const memoKey = tab === "minute" ? `minute:${minuteScope}:${minuteUnit}` : tab;
    // 이미 받은 조합이면 메모에서 즉시 표시(네트워크 0).
    const memo = candlesCacheRef.current.get(memoKey);
    if (memo) {
      setCandles(memo);
      setError(null);
      setLoading(false);
      return;
    }
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

    fetchChart(symbol, tab, {
      signal: controller.signal,
      unit: tab === "minute" ? minuteUnit : undefined,
      scope: tab === "minute" ? minuteScope : undefined,
    })
      .then((d) => {
        if (!alive) return;
        if (d.candles.length === 0 && scheduleRetry()) return;
        if (d.candles.length > 0) candlesCacheRef.current.set(memoKey, d.candles);
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
  }, [symbol, tab, minuteUnit, minuteScope, fetchChart, retryCount]);

  // 기업개요 조회 (기업개요 탭일 때만)
  useEffect(() => {
    if (tab !== "overview" || !fetchOverview) return;
    let alive = true;
    setOvLoading(true);
    setOvError(null);
    fetchOverview(symbol)
      .then((d) => {
        if (alive) {
          setOverview(d);
          setOvLoading(false);
        }
      })
      .catch(() => {
        if (alive) {
          setOvError("기업개요를 불러올 수 없습니다");
          setOvLoading(false);
        }
      });
    return () => {
      alive = false;
    };
  }, [tab, symbol, fetchOverview]);

  // 차트 렌더
  useEffect(() => {
    const el = containerRef.current;
    if (!el || tab === "overview" || candles.length === 0) return;

    const chart: IChartApi = createChart(el, {
      width: el.clientWidth,
      height: el.clientHeight,
      layout: { background: { color: "#ffffff" }, textColor: "#1b1f24" },
      grid: { vertLines: { color: "#eef1f4" }, horzLines: { color: "#eef1f4" } },
      timeScale: {
        timeVisible: tab === "minute",
        borderColor: "#e3e6ea",
        // 데이터 양 끝을 차트 가장자리에 고정 → 줌 아웃/스크롤해도 빈 공백이 생기지 않는다.
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
      },
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
  }, [candles, tab]);

  const tabButton = (value: ChartTab, label: string) => (
    <button
      role="tab"
      aria-selected={tab === value}
      className={tab === value ? "active" : ""}
      onClick={() => setTab(value)}
    >
      {label}
    </button>
  );

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
          <div className="chart-toggle" role="tablist" aria-label="차트/정보 보기">
            {tabButton("overview", "기업개요")}
            {tabButton("daily", "일봉")}
            {tabButton("weekly", "주봉")}
            {tabButton("minute", "분봉")}
          </div>
          {tab === "minute" && minuteScope === "session" && (
            <div className="minute-units" role="tablist" aria-label="분봉 단위">
              {MINUTE_UNITS.map((u) => (
                <button
                  key={u}
                  role="tab"
                  aria-selected={minuteUnit === u}
                  className={minuteUnit === u ? "active" : ""}
                  onClick={() => setMinuteUnit(u)}
                >
                  {u}분
                </button>
              ))}
            </div>
          )}
          <button className="modal-close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </header>

        <div className="chart-body">
          {tab === "overview" ? (
            <div className="company-overview">
              {ovLoading && <p className="muted">불러오는 중...</p>}
              {ovError && <p className="error">{ovError}</p>}
              {!ovLoading && !ovError && overview && (() => {
                const hasAny =
                  overview.summary.length > 0 ||
                  (overview.price?.length ?? 0) > 0 ||
                  (overview.shareholders?.length ?? 0) > 0;
                if (!hasAny) return <p className="empty">기업개요가 없습니다</p>;
                return (
                  <>
                    {overview.base_date && (
                      <p className="muted overview-date">기준: {overview.base_date}</p>
                    )}
                    {overview.summary.length > 0 && (
                      <ul className="overview-list">
                        {overview.summary.map((line, i) => (
                          <li key={i}>{line}</li>
                        ))}
                      </ul>
                    )}
                    {overview.history && overview.history.length > 0 && (
                      <table className="overview-table history">
                        <caption>최근연혁</caption>
                        <tbody>
                          {overview.history.map((h, i) => (
                            <tr key={i}>
                              <th>{h.date}</th>
                              <td>{h.detail}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {overview.products && overview.products.length > 0 && (
                      <table className="overview-table products">
                        <caption>주요제품 매출구성</caption>
                        <thead>
                          <tr>
                            <th>제품</th>
                            <th>구성비</th>
                          </tr>
                        </thead>
                        <tbody>
                          {overview.products.map((p, i) => {
                            const w = Math.max(0, Math.min(100, parseFloat(p.pct) || 0));
                            return (
                              <tr key={i}>
                                <td className="bar-cell">
                                  <span className="bar-fill" style={{ width: `${w}%` }} />
                                  <span className="bar-label">{p.name}</span>
                                </td>
                                <td className="num">{p.pct}%</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                    {overview.price && overview.price.length > 0 && (
                      <table className="overview-table">
                        <caption>시세</caption>
                        <tbody>
                          {overview.price.map((p) => (
                            <tr key={p.label}>
                              <th>{p.label}</th>
                              <td>{p.value}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {overview.shareholders && overview.shareholders.length > 0 && (
                      <table className="overview-table shareholders">
                        <caption>주주현황</caption>
                        <thead>
                          <tr>
                            <th>주요주주</th>
                            <th>보유주식수</th>
                            <th>지분율</th>
                          </tr>
                        </thead>
                        <tbody>
                          {overview.shareholders.map((s, i) => (
                            <tr key={i}>
                              <td>{s.name}</td>
                              <td className="num">{s.shares ?? "-"}</td>
                              <td className="num">{s.pct != null ? `${s.pct}%` : "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    <p className="muted overview-source">출처: 네이버금융 종목분석</p>
                  </>
                );
              })()}
            </div>
          ) : (
            <>
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
