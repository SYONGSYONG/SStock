import { useCallback, useEffect, useState } from "react";
import type { TradePnlResult, TradingMode } from "../types";
import { fmt, fmtRate, direction } from "../lib/format";

interface TradePnlPageProps {
  mode: TradingMode;
  fetchTradePnl: (
    mode: TradingMode,
    opts?: { start?: string; end?: string; symbol?: string; sort?: "desc" | "asc" },
  ) => Promise<TradePnlResult>;
}

/** 로컬(브라우저) 날짜를 YYYY-MM-DD로. */
function todayStr(): string {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

export function TradePnlPage({ mode, fetchTradePnl }: TradePnlPageProps) {
  const [start, setStart] = useState(todayStr());
  const [end, setEnd] = useState(todayStr());
  const [sort, setSort] = useState<"desc" | "asc">("desc");
  const [symbol, setSymbol] = useState(""); // "" = 전체
  // 종목 드롭다운 옵션(전체 조회 결과에서 누적). 필터 중에도 목록을 유지한다.
  const [symbolOptions, setSymbolOptions] = useState<{ code: string; name: string }[]>([]);
  const [result, setResult] = useState<TradePnlResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchTradePnl(mode, {
        start,
        end,
        sort,
        symbol: symbol || undefined,
      });
      setResult(res);
      // 종목 미선택(전체) 조회일 때만 드롭다운 목록을 갱신한다.
      if (!symbol) {
        const seen = new Map<string, string>();
        for (const r of res.rows) if (!seen.has(r.symbol)) seen.set(r.symbol, r.name);
        setSymbolOptions([...seen].map(([code, name]) => ({ code, name })));
      }
    } catch {
      setError("조회 실패");
    } finally {
      setLoading(false);
    }
  }, [mode, start, end, sort, symbol, fetchTradePnl]);

  // 모드 전환 시 종목 필터 초기화(모드별 격리)
  useEffect(() => {
    setSymbol("");
  }, [mode]);

  // 모드/종목 변경 시 자동 재조회(기간·정렬은 '조회' 버튼으로 적용)
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, symbol]);

  const rows = result?.rows ?? [];
  const summary = result?.summary;

  return (
    <section className="trade-pnl">
      <div className="panel-head-row">
        <h2>기간별 매매손익</h2>
        <span className="head-hint">
          {mode === "live" ? "실전" : "모의"} · 봇 주문 이력 기준
          {result?.estimated && " · 수수료·세금은 추정치"}
        </span>
      </div>

      <form
        className="pnl-filter"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <label>
          조회기간
          <input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} />
        </label>
        <span className="tilde">~</span>
        <input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
        <label className="pnl-symbol">
          종목
          <select
            aria-label="종목 선택"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          >
            <option value="">전체</option>
            {symbolOptions.map((o) => (
              <option key={o.code} value={o.code}>
                {o.name ? `${o.name} (${o.code})` : o.code}
              </option>
            ))}
          </select>
        </label>
        <div className="pnl-sort" role="group" aria-label="정렬">
          <button
            type="button"
            className={sort === "desc" ? "active" : ""}
            onClick={() => setSort("desc")}
          >
            역순
          </button>
          <button
            type="button"
            className={sort === "asc" ? "active" : ""}
            onClick={() => setSort("asc")}
          >
            정순
          </button>
        </div>
        <button type="submit" className="pnl-search">
          조회
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && !result.available && (
        <p className="error">
          실전 매매손익을 KIS에서 불러올 수 없습니다(자격증명 또는 KIS 조회 오류).
        </p>
      )}

      <div className="pnl-table-wrap">
        <table className="pnl-table">
          <thead>
            <tr>
              <th>매매일자</th>
              <th>종목명</th>
              <th>종목코드</th>
              <th>구분</th>
              <th className="num">매도수량</th>
              <th className="num">매입단가</th>
              <th className="num">매도단가</th>
              <th className="num">매수금액</th>
              <th className="num">매도금액</th>
              <th className="num">수수료</th>
              <th className="num">제세금</th>
              <th className="num">실현손익</th>
              <th className="num">손익률</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const dir = direction(r.realized_pnl);
              return (
                <tr key={`${r.symbol}-${r.trade_date}-${i}`}>
                  <td>{r.trade_date}</td>
                  <td>{r.name || "-"}</td>
                  <td className="code">{r.symbol}</td>
                  <td>
                    <span className={`src-badge src-${r.source}`}>
                      {r.source === "bot" ? "봇" : "직접"}
                    </span>
                  </td>
                  <td className="num">{fmt(r.sell_qty)}</td>
                  <td className="num">{fmt(r.buy_unit_price)}</td>
                  <td className="num">{fmt(r.sell_unit_price)}</td>
                  <td className="num">{fmt(r.buy_amount)}</td>
                  <td className="num">{fmt(r.sell_amount)}</td>
                  <td className="num muted">{fmt(r.fee)}</td>
                  <td className="num muted">{fmt(r.tax)}</td>
                  <td className={`num ${dir}`}>{fmt(r.realized_pnl)}</td>
                  <td className={`num ${dir}`}>{fmtRate(r.pnl_rate)}</td>
                </tr>
              );
            })}
            {rows.length === 0 && !loading && (
              <tr>
                <td colSpan={13} className="empty">
                  해당 기간의 매매손익이 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {summary && rows.length > 0 && (
        <div className="pnl-summary">
          <table className="pnl-summary-table">
            <thead>
              <tr>
                <th></th>
                <th className="num">수량</th>
                <th className="num">거래금액</th>
                <th className="num">수수료</th>
                <th className="num">제세금</th>
                <th className="num">정산금액</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th>매도</th>
                <td className="num">{fmt(summary.sell.qty)}</td>
                <td className="num">{fmt(summary.sell.amount)}</td>
                <td className="num">{fmt(summary.sell.fee)}</td>
                <td className="num">{fmt(summary.sell.tax)}</td>
                <td className="num">{fmt(summary.sell.settle)}</td>
              </tr>
              <tr>
                <th>매수</th>
                <td className="num">{fmt(summary.buy.qty)}</td>
                <td className="num">{fmt(summary.buy.amount)}</td>
                <td className="num">{fmt(summary.buy.fee)}</td>
                <td className="num">{fmt(summary.buy.tax)}</td>
                <td className="num">{fmt(summary.buy.settle)}</td>
              </tr>
            </tbody>
          </table>
          <div className="pnl-total">
            <div>
              <span className="pnl-total-label">실현손익 합계</span>
              <strong className={direction(summary.realized_pnl_total)}>
                {fmt(summary.realized_pnl_total)}원
              </strong>
            </div>
            <div>
              <span className="pnl-total-label">총손익률</span>
              <strong className={direction(summary.total_pnl_rate)}>
                {fmtRate(summary.total_pnl_rate)}
              </strong>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
