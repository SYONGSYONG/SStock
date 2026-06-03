import type { Position, Quote } from "../types";
import { direction, fmt, fmtRate } from "../lib/format";

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
              <th className="num">평단</th>
              <th className="num">현재가</th>
              <th className="num">평가금액</th>
              <th className="num">손익</th>
              <th className="num">손익률</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const q = quotes[p.symbol];
              const currentPrice = q?.price ?? p.price ?? null;
              const evalAmount = p.eval_amount ?? (currentPrice != null ? currentPrice * p.qty : null);
              const plAmount = p.pl_amount ?? null;
              const plRate = p.pl_rate ?? null;
              return (
                <tr key={p.symbol}>
                  <td>
                    <span className="code">{p.symbol}</span>{" "}
                    <span className="name">{p.name ?? ""}</span>
                  </td>
                  <td className="num">{fmt(p.qty)}</td>
                  <td className="num">{fmt(p.avg_price)}</td>
                  <td className={`num ${direction(q?.change)}`}>{fmt(currentPrice)}</td>
                  <td className="num">{fmt(evalAmount)}</td>
                  <td className={`num ${plAmount != null && plAmount !== 0 ? direction(plAmount) : ""}`}>
                    {fmt(plAmount)}
                  </td>
                  <td className="num">{fmtRate(plRate)}</td>
                </tr>
              );
            })}
            {positions.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">
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
