import type { Budget } from "../types";
import { fmt } from "../lib/format";

interface BudgetPanelProps {
  budgets: Budget[];
  orderableCash?: number | null; // 계좌 주문가능현금(/api/account/balance)
  error?: string | null;
}

/** 자본 칸막이 요약: 종목별 칸막이는 전략 항목 아래에서 표시·수정하므로
 *  여기서는 현금 대비 설정 현황 요약만 보여준다(종목 중복 표기 제거). */
export function BudgetPanel({ budgets, orderableCash, error }: BudgetPanelProps) {
  // 설정가능금액 = 주문가능현금 − Σ(각 칸막이 가용액)
  const committed = budgets.reduce((sum, b) => sum + b.available, 0);
  const settable = orderableCash == null ? null : orderableCash - committed;

  return (
    <div className="panel-section">
      <h2>자본 칸막이</h2>
      <p className="muted hint">
        종목별 투입 원금 한도 (한도 = 원금 + 실현손익) · 종목별 현황·수정은 위 전략 목록에서
      </p>
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
      <p className="muted hint">
        {budgets.length > 0
          ? `설정된 칸막이 ${budgets.length}종목`
          : "설정된 칸막이가 없습니다 — 전략 추가 시 함께 등록됩니다"}
      </p>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
