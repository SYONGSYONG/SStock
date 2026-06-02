import type { Position, Quote } from "../types";
import { direction, fmt } from "../lib/format";

interface PositionTableProps {
  positions: Position[];
  quotes: Record<string, Quote>;
}

export function PositionTable({ positions, quotes }: PositionTableProps) {
  return (
    <section className="panel">
      <h2>보유 포지션</h2>
      <div className="table-scroll">
      <table className="quote-table">
        <thead>
          <tr>
            <th>종목</th>
            <th className="num">수량</th>
            <th className="num">현재가</th>
            <th className="num">평가금액</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            const q = quotes[p.symbol];
            const evalAmount = q?.price != null ? q.price * p.qty : null;
            return (
              <tr key={p.symbol}>
                <td>
                  <span className="code">{p.symbol}</span>{" "}
                  <span className="name">{p.name ?? ""}</span>
                </td>
                <td className="num">{fmt(p.qty)}</td>
                <td className={`num ${direction(q?.change)}`}>{fmt(q?.price)}</td>
                <td className="num">{fmt(evalAmount)}</td>
              </tr>
            );
          })}
          {positions.length === 0 && (
            <tr>
              <td colSpan={4} className="empty">
                보유 포지션이 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
    </section>
  );
}
