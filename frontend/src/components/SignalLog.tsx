import type { Signal } from "../types";
import { fmt } from "../lib/format";
import { strategyLabel } from "../lib/strategy";

interface SignalLogProps {
  signals: Signal[];
}

export function SignalLog({ signals }: SignalLogProps) {
  return (
    <section className="panel">
      <h2>매매 신호</h2>
      <div className="table-scroll">
      <table className="quote-table">
        <thead>
          <tr>
            <th>시각</th>
            <th>종목</th>
            <th>전략</th>
            <th>구분</th>
            <th className="num">가격</th>
            <th>근거</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id}>
              <td className="muted">{s.created_at?.slice(11, 19) ?? "-"}</td>
              <td className="code">{s.symbol}</td>
              <td>{strategyLabel(s.strategy)}</td>
              <td className={s.side === "BUY" ? "up" : "down"}>
                {s.side === "BUY" ? "매수" : "매도"}
              </td>
              <td className="num">{fmt(s.price)}</td>
              <td className="muted">{s.reason}</td>
            </tr>
          ))}
          {signals.length === 0 && (
            <tr>
              <td colSpan={6} className="empty">
                아직 신호가 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </section>
  );
}
