import type { Quote, WatchItem } from "../types";
import { direction, fmt, fmtRate } from "../lib/format";

interface QuoteTableProps {
  items: WatchItem[];
  quotes: Record<string, Quote>;
}

export function QuoteTable({ items, quotes }: QuoteTableProps) {
  return (
    <section className="panel">
      <h2>실시간 시세</h2>
      <div className="table-scroll">
      <table className="quote-table">
        <thead>
          <tr>
            <th>종목</th>
            <th className="num">현재가</th>
            <th className="num">전일대비</th>
            <th className="num">등락률</th>
            <th className="num">거래량</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => {
            const q = quotes[it.symbol];
            const dir = direction(q?.change);
            return (
              <tr key={it.symbol}>
                <td>
                  <span className="code">{it.symbol}</span>{" "}
                  <span className="name">{it.name ?? ""}</span>
                </td>
                <td className={`num ${dir}`}>{fmt(q?.price)}</td>
                <td className={`num ${dir}`}>{fmt(q?.change)}</td>
                <td className={`num ${dir}`}>{fmtRate(q?.change_rate)}</td>
                <td className="num">{fmt(q?.volume)}</td>
              </tr>
            );
          })}
          {items.length === 0 && (
            <tr>
              <td colSpan={5} className="empty">
                관심종목을 추가하세요
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </section>
  );
}
