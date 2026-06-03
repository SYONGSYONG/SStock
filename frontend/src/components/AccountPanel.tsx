import type { AccountBalance } from "../types";
import { direction, fmt } from "../lib/format";

interface AccountPanelProps {
  balance: AccountBalance | null;
}

/** 계좌 잔고 요약 — KIS 주식잔고조회(output2) 기반 예수금/주문가능/총평가/평가손익/순자산. */
export function AccountPanel({ balance }: AccountPanelProps) {
  // balance === null: 아직 첫 조회 전(로딩 중). available === false: KIS 오류(조회 불가).
  const loading = balance === null;
  const unavailable = balance !== null && !balance.available;

  return (
    <section className="panel account-panel">
      <div className="account-head">
        <h2>계좌 잔고</h2>
        {balance && <span className={`badge ${balance.mode === "live" ? "cat-error" : "cat-mode"}`}>
          {balance.mode === "live" ? "실전" : "모의"}
        </span>}
        {loading && <span className="muted account-note">불러오는 중…</span>}
        {unavailable && <span className="muted account-note">조회 불가</span>}
      </div>
      <div className="account-grid">
        <Stat label="예수금" value={balance?.deposit} />
        <Stat label="주문가능현금" value={balance?.orderable_cash} accent />
        <Stat label="총평가금액" value={balance?.total_eval} />
        <Stat label="평가손익" value={balance?.eval_pnl} signed />
        <Stat label="순자산" value={balance?.net_asset} />
      </div>
    </section>
  );
}

interface StatProps {
  label: string;
  value: number | null | undefined;
  signed?: boolean; // 평가손익: 부호+색상
  accent?: boolean; // 주문가능현금 강조
}

function Stat({ label, value, signed, accent }: StatProps) {
  const dir = signed ? direction(value) : "neutral";
  const sign = signed && value != null && value > 0 ? "+" : "";
  return (
    <div className={`account-stat${accent ? " accent" : ""}`}>
      <span className="account-label">{label}</span>
      <span className={`account-value num ${dir}`}>
        {value == null ? "-" : `${sign}${fmt(value)}`}
        <span className="account-unit">원</span>
      </span>
    </div>
  );
}
