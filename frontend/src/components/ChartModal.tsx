import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";
import type { ChartData, ChartInterval, CompanyOverview, MinuteUnit } from "../types";
import { buildExtremaMarkers, findExtrema, type ExtremaPoint } from "../lib/chartMarkers";
import { MA_CONFIGS, buildMaLineData, buildTooltipData } from "../lib/chartIndicators";

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

/**
 * tooltip 박스 내용을 DOM으로 채운다. innerHTML 대신 textContent로 구성해
 * 값 주입을 안전하게 한다(XSS 회피). 이평 그룹은 거래량 다음에 구분선으로 나눈다.
 */
function fillTooltip(node: HTMLDivElement, data: ReturnType<typeof buildTooltipData>) {
  node.replaceChildren();
  if (!data) return;

  const head = document.createElement("div");
  head.className = "tt-time";
  head.textContent = data.time;
  node.appendChild(head);

  data.rows.forEach((row) => {
    // 이평 첫 행 앞에 구분선 + 소제목
    if (row.label === "이평5") {
      const sep = document.createElement("div");
      sep.className = "tt-sep";
      sep.textContent = "주가이동평균";
      node.appendChild(sep);
    }
    const r = document.createElement("div");
    r.className = "tt-row";
    const label = document.createElement("span");
    label.className = "tt-label";
    label.textContent = row.label;
    const val = document.createElement("span");
    val.className = "tt-value";
    val.textContent = row.value;
    const chg = document.createElement("span");
    chg.className = `tt-change${row.dir ? ` ${row.dir}` : ""}`;
    chg.textContent = row.change ?? "";
    r.append(label, val, chg);
    node.appendChild(r);
  });
}

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

    // 최고가·최저가 화살표 마커(텍스트는 제거하고 화살표만) — 텍스트는 아래 HTML
    // 오버레이로 표시해 가장자리 봉에서도 잘리지 않게 안쪽으로 밀어준다.
    const arrowMarkers = buildExtremaMarkers(candles, UP, DOWN).map((m) => ({ ...m, text: "" }));
    if (arrowMarkers.length > 0) {
      createSeriesMarkers(candleSeries, arrowMarkers);
    }

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

    // 이동평균선(5/20/60/120) — 캔들과 같은 가격축에 겹쳐 그린다.
    // 워밍업 구간은 점이 없어 데이터가 충분한 구간부터 선이 시작된다.
    for (const cfg of MA_CONFIGS) {
      const lineData = buildMaLineData(candles, cfg.period);
      if (lineData.length === 0) continue;
      const line = chart.addSeries(LineSeries, {
        color: cfg.color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      line.setData(lineData.map((p) => ({ time: p.time as never, value: p.value })));
    }

    chart.timeScale().fitContent();

    // 최고/최저 라벨을 HTML 오버레이로 띄운다. 마커 텍스트는 봉 중앙 정렬이라 양
    // 가장자리(첫 봉=최저, 끝 봉=최고)에서 잘리므로, 라벨을 차트 안쪽으로 클램프한다.
    const extrema = findExtrema(candles);
    const labelEls: HTMLDivElement[] = [];
    let updateLabels = () => {};
    if (extrema) {
      const timeScale = chart.timeScale();
      const makeLabel = (pt: ExtremaPoint): HTMLDivElement => {
        const node = document.createElement("div");
        node.className = `chart-extrema-label ${pt.kind === "high" ? "is-high" : "is-low"}`;
        node.textContent = pt.label;
        el.appendChild(node);
        labelEls.push(node);
        return node;
      };
      const highEl = makeLabel(extrema.high);
      const lowEl = extrema.low ? makeLabel(extrema.low) : null;

      const placeLabel = (node: HTMLDivElement, pt: ExtremaPoint) => {
        const x = timeScale.timeToCoordinate(pt.time as Time);
        const y = candleSeries.priceToCoordinate(pt.price);
        if (x == null || y == null) {
          node.style.visibility = "hidden";
          return;
        }
        node.style.visibility = "visible";
        const w = node.offsetWidth;
        const h = node.offsetHeight;
        // 좌우로 차트 안에 들어오도록 클램프(가장자리에서 안쪽으로 밀림)
        const left = Math.max(4, Math.min(x - w / 2, el.clientWidth - w - 4));
        const rawTop = pt.kind === "high" ? y - h - 10 : y + 10;
        const top = Math.max(2, Math.min(rawTop, el.clientHeight - h - 2));
        node.style.left = `${left}px`;
        node.style.top = `${top}px`;
      };

      updateLabels = () => {
        placeLabel(highEl, extrema.high);
        if (lowEl && extrema.low) placeLabel(lowEl, extrema.low);
      };
      updateLabels();
      timeScale.subscribeVisibleLogicalRangeChange(updateLabels);
    }

    // 마우스 시점 tooltip — 가리키는 봉의 OHLC·거래량·이평을 박스로 표시한다.
    // whitespace 없이 캔들을 넣었으므로 logical 인덱스 = candles 배열 인덱스.
    const tooltipEl = document.createElement("div");
    tooltipEl.className = "chart-tooltip";
    tooltipEl.style.display = "none";
    el.appendChild(tooltipEl);

    const onCrosshair = (param: MouseEventParams) => {
      if (!param.point || param.logical == null) {
        tooltipEl.style.display = "none";
        return;
      }
      const idx = Math.round(param.logical as number);
      const data = buildTooltipData(candles, idx);
      if (!data) {
        tooltipEl.style.display = "none";
        return;
      }
      fillTooltip(tooltipEl, data);
      tooltipEl.style.display = "block";
      // 커서 옆에 띄우되 차트 안으로 클램프(가장자리 잘림 방지)
      const w = tooltipEl.offsetWidth;
      const h = tooltipEl.offsetHeight;
      let left = param.point.x + 16;
      if (left + w > el.clientWidth) left = param.point.x - w - 16;
      left = Math.max(4, Math.min(left, el.clientWidth - w - 4));
      const top = Math.max(4, Math.min(param.point.y + 12, el.clientHeight - h - 4));
      tooltipEl.style.left = `${left}px`;
      tooltipEl.style.top = `${top}px`;
    };
    chart.subscribeCrosshairMove(onCrosshair);

    const onResize = () => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
      updateLabels();
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.unsubscribeCrosshairMove(onCrosshair);
      tooltipEl.remove();
      if (extrema) chart.timeScale().unsubscribeVisibleLogicalRangeChange(updateLabels);
      labelEls.forEach((node) => node.remove());
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
    // 배경 클릭/Esc로는 닫히지 않는다. 우상단 X(modal-close)로만 닫는다(실수 닫힘 방지).
    <div className="modal-backdrop">
      <div
        className="modal chart-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${symbol} 차트`}
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
