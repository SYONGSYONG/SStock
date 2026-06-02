import { useState } from "react";
import type { Budget, WatchItem } from "../types";
import { fmt } from "../lib/format";

interface BudgetPanelProps {
  budgets: Budget[];
  items: WatchItem[];
  onSet: (symbol: string, principal: number) => void;
  onRemove: (symbol: string) => void;
  error?: string | null;
}

export function BudgetPanel({ budgets, items, onSet, onRemove, error }: BudgetPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [principal, setPrincipal] = useState("");

  const nameOf = (s: string) => items.find((it) => it.symbol === s)?.name ?? "";

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = Number(principal);
    if (!/^\d{6}$/.test(symbol) || !Number.isFinite(p) || p < 1) return;
    onSet(symbol, Math.floor(p));
    setSymbol("");
    setPrincipal("");
  };

  return (
    <section className="panel">
      <h2>자본 칸막이</h2>
      <p className="muted hint">종목별 투입 원금 한도 (한도 = 원금 + 실현손익)</p>
      <form className="budget-form" onSubmit={submit}>
        <input
          aria-label="칸막이 종목코드"
          placeholder="종목코드"
          value={symbol}
          maxLength={6}
          onChange={(e) => setSymbol(e.target.value.replace(/\D/g, ""))}
        />
        <input
          aria-label="원금"
          placeholder="원금(원)"
          inputMode="numeric"
          value={principal}
          onChange={(e) => setPrincipal(e.target.value.replace(/\D/g, ""))}
        />
        <button type="submit" disabled={!/^\d{6}$/.test(symbol) || !principal}>
          설정
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul className="strategy-list">
        {budgets.map((b) => (
          <li key={b.symbol} className="strategy-item">
            <div className="strategy-head">
              <span className="code">{b.symbol}</span>
              <span className="name">{nameOf(b.symbol)}</span>
              <span className="spacer" />
              <button className="link-danger" onClick={() => onRemove(b.symbol)}>
                해제
              </button>
            </div>
            <div className="strategy-desc">
              가용 <b className={b.available < 0 ? "down" : undefined}>{fmt(b.available)}</b> / 한도{" "}
              {fmt(b.ceiling)}원
              {b.realized_pnl !== 0 && (
                <span className={b.realized_pnl > 0 ? "up" : "down"}>
                  {" "}(실현 {b.realized_pnl > 0 ? "+" : ""}
                  {fmt(b.realized_pnl)})
                </span>
              )}
            </div>
          </li>
        ))}
        {budgets.length === 0 && <li className="empty">설정된 칸막이가 없습니다</li>}
      </ul>
    </section>
  );
}
