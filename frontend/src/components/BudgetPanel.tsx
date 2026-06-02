import { useState } from "react";
import type { Budget, WatchItem } from "../types";
import { fmt } from "../lib/format";

interface BudgetPanelProps {
  budgets: Budget[];
  items: WatchItem[];
  onSet: (symbol: string, principal: number) => void;
  onRemove: (symbol: string) => void;
  orderableCash?: number | null; // 계좌 주문가능현금(/api/account/balance)
  error?: string | null;
}

export function BudgetPanel({
  budgets,
  items,
  onSet,
  onRemove,
  orderableCash,
  error,
}: BudgetPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [principal, setPrincipal] = useState("");

  const nameOf = (s: string) => items.find((it) => it.symbol === s)?.name ?? "";

  // 설정가능금액 = 주문가능현금 − Σ(각 칸막이 가용액)
  const committed = budgets.reduce((sum, b) => sum + b.available, 0);
  const settable = orderableCash == null ? null : orderableCash - committed;
  const inputAmount = Number(principal) || 0;
  const overSettable = settable != null && inputAmount > settable; // 표시+경고만(차단 안 함)

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
      <p className="budget-cash">
        {orderableCash == null ? (
          <span className="muted">주문가능현금 조회 불가</span>
        ) : (
          <>
            주문가능현금 {fmt(orderableCash)}원 · 설정가능{" "}
            <b className={settable != null && settable < 0 ? "down" : "up"}>{fmt(settable)}</b>원
            {settable != null && settable < 0 && (
              <span className="down"> (칸막이 합계가 현금 초과)</span>
            )}
          </>
        )}
      </p>
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
      {overSettable && (
        <p className="budget-warn">
          ⚠ 설정가능금액({fmt(settable)}원)을 초과합니다 — 설정은 가능하나 계좌 현금이 부족할 수
          있습니다
        </p>
      )}
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
