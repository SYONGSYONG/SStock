import { useState } from "react";
import type { Budget, WatchItem } from "../types";
import { fmt } from "../lib/format";
import { Modal } from "./Modal";

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
  // 원금 수정 모달
  const [editing, setEditing] = useState<Budget | null>(null);
  const [editPrincipal, setEditPrincipal] = useState("");

  const nameOf = (s: string) => items.find((it) => it.symbol === s)?.name ?? "";

  const openEdit = (b: Budget) => {
    setEditing(b);
    setEditPrincipal(String(b.principal));
  };

  const editValue = Number(editPrincipal);
  const editValid = /^\d+$/.test(editPrincipal) && editValue >= 1;

  const saveEdit = () => {
    if (!editing || !editValid) return;
    onSet(editing.symbol, Math.floor(editValue));
    setEditing(null);
  };

  // 설정가능금액 = 주문가능현금 − Σ(각 칸막이 가용액)
  const committed = budgets.reduce((sum, b) => sum + b.available, 0);
  const settable = orderableCash == null ? null : orderableCash - committed;

  return (
    <div className="panel-section">
      <h2>자본 칸막이</h2>
      <p className="muted hint">종목별 투입 원금 한도 (한도 = 원금 + 실현손익) · 전략 추가 시 함께 등록</p>
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
      {error && <p className="error">{error}</p>}
      <ul className="strategy-list">
        {budgets.map((b) => (
          <li key={b.symbol} className="strategy-item">
            <div className="strategy-head">
              <span className="code">{b.symbol}</span>
              <span className="name">{nameOf(b.symbol)}</span>
              <span className="spacer" />
              <button className="link-action" onClick={() => openEdit(b)}>
                수정
              </button>
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
        {budgets.length === 0 && (
          <li className="empty">설정된 칸막이가 없습니다 — 전략 추가 시 함께 등록됩니다</li>
        )}
      </ul>

      {editing && (
        <Modal
          title={`${editing.symbol} ${nameOf(editing.symbol)} · 원금 수정`}
          onClose={() => setEditing(null)}
        >
          <label className="param-field">
            <span className="param-label">원금(원)</span>
            <input
              type="text"
              aria-label="수정 원금"
              inputMode="numeric"
              value={editPrincipal}
              onChange={(e) => setEditPrincipal(e.target.value.replace(/\D/g, ""))}
            />
            <span className="param-default">현재 {fmt(editing.principal)}원</span>
          </label>
          <div className="edit-modal-actions">
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>
              취소
            </button>
            <button
              type="button"
              className="strategy-add"
              disabled={!editValid}
              onClick={saveEdit}
            >
              저장
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
