import { useState } from "react";
import type { RiskLimit, TradingMode } from "../types";
import { fmt } from "../lib/format";
import { direction } from "../lib/format";

interface RiskLimitBarProps {
  data: RiskLimit | null;
  mode: TradingMode;
  onUpdate: (
    maxOrders: number,
    maxAmount: number,
    maxDailyLoss: number,
  ) => Promise<void> | void;
  error?: string | null;
}

/** 사용량 비율(0~1). 한도가 0이면 0으로 처리. */
function ratio(used: number, max: number): number {
  if (max <= 0) return 0;
  return Math.min(1, used / max);
}

export function RiskLimitBar({ data, mode, onUpdate, error }: RiskLimitBarProps) {
  const [editing, setEditing] = useState(false);
  const [orders, setOrders] = useState("");
  const [amount, setAmount] = useState("");
  const [dailyLoss, setDailyLoss] = useState("");
  const isLive = mode === "live";

  const startEdit = () => {
    if (!data) return;
    setOrders(String(data.max_orders));
    setAmount(String(data.max_amount));
    setDailyLoss(String(data.max_daily_loss));
    setEditing(true);
  };

  const submit = async () => {
    const o = Number(orders);
    const a = Number(amount);
    const dl = Number(dailyLoss);
    if (!Number.isInteger(o) || o < 1 || !Number.isInteger(a) || a < 1) {
      window.alert("주문 횟수·금액은 1 이상의 정수여야 합니다.");
      return;
    }
    if (!Number.isInteger(dl) || dl < 0) {
      window.alert("하루 손실 한도는 0 이상의 정수여야 합니다(0=비활성).");
      return;
    }
    // 한도 변경은 매매 안전에 직접 영향 → 적용 전 재확인(사용자 요구사항).
    const ok = window.confirm(
      `${isLive ? "실전" : "모의"} 일일 한도를 변경합니다.\n` +
        `· 주문 횟수: ${fmt(data?.max_orders ?? 0)} → ${fmt(o)}건\n` +
        `· 주문 금액: ${fmt(data?.max_amount ?? 0)} → ${fmt(a)}원\n` +
        `· 하루 손실 한도: ${fmt(data?.max_daily_loss ?? 0)} → ${fmt(dl)}원${dl === 0 ? "(비활성)" : ""}\n\n계속하시겠습니까?`,
    );
    if (!ok) return;
    await onUpdate(o, a, dl);
    setEditing(false);
  };

  const orderRatio = data ? ratio(data.order_count, data.max_orders) : 0;
  const amountRatio = data ? ratio(data.order_amount, data.max_amount) : 0;
  // 손실 사용률: 실현손익이 음수일 때 손실/한도(한도 0이면 0).
  const lossRatio =
    data && data.max_daily_loss > 0 && data.realized_pnl < 0
      ? ratio(-data.realized_pnl, data.max_daily_loss)
      : 0;

  return (
    <section className="panel risk-limit" aria-label="일일 주문 한도">
      <div className="panel-head-row">
        <h2>오늘 주문 한도</h2>
        {!editing && (
          <button className="btn-ghost risk-edit-btn" onClick={startEdit} disabled={!data}>
            제한 변경
          </button>
        )}
      </div>

      {!data ? (
        <p className="muted">불러오는 중…</p>
      ) : editing ? (
        <div className="risk-edit">
          <label>
            일일 주문 횟수
            <input
              type="number"
              min={1}
              value={orders}
              onChange={(e) => setOrders(e.target.value)}
            />
            <span className="unit">건</span>
          </label>
          <label>
            일일 주문 금액
            <input
              type="number"
              min={1}
              step={100000}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <span className="unit">원</span>
          </label>
          <label>
            하루 손실 한도
            <input
              type="number"
              min={0}
              step={100000}
              value={dailyLoss}
              onChange={(e) => setDailyLoss(e.target.value)}
            />
            <span className="unit">원</span>
          </label>
          <div className="risk-edit-actions">
            <button className="risk-save" onClick={submit}>
              저장
            </button>
            <button className="btn-ghost" onClick={() => setEditing(false)}>
              취소
            </button>
          </div>
        </div>
      ) : (
        <div className="risk-metrics">
          <div className="risk-metric">
            <div className="risk-metric-head">
              <span className="risk-label">주문 횟수</span>
              <span className="risk-value">
                <strong className={orderRatio >= 1 ? "over" : undefined}>
                  {fmt(data.order_count)}
                </strong>
                <span className="risk-sep"> / </span>
                {fmt(data.max_orders)}건
              </span>
            </div>
            <div className="risk-track">
              <div
                className={`risk-fill${orderRatio >= 1 ? " over" : ""}`}
                style={{ width: `${orderRatio * 100}%` }}
              />
            </div>
          </div>
          <div className="risk-metric">
            <div className="risk-metric-head">
              <span className="risk-label">주문 금액</span>
              <span className="risk-value">
                <strong className={amountRatio >= 1 ? "over" : undefined}>
                  {fmt(data.order_amount)}
                </strong>
                <span className="risk-sep"> / </span>
                {fmt(data.max_amount)}원
              </span>
            </div>
            <div className="risk-track">
              <div
                className={`risk-fill${amountRatio >= 1 ? " over" : ""}`}
                style={{ width: `${amountRatio * 100}%` }}
              />
            </div>
          </div>
          <div className="risk-metric">
            <div className="risk-metric-head">
              <span className="risk-label">오늘 실현손익</span>
              <span className="risk-value">
                <strong className={direction(data.realized_pnl)}>
                  {fmt(data.realized_pnl)}
                </strong>
                {data.max_daily_loss > 0 && (
                  <>
                    <span className="risk-sep"> / 손실한도 </span>
                    −{fmt(data.max_daily_loss)}원
                  </>
                )}
              </span>
            </div>
            {data.max_daily_loss > 0 && (
              <div className="risk-track">
                <div
                  className={`risk-fill${lossRatio >= 1 ? " over" : " down"}`}
                  style={{ width: `${lossRatio * 100}%` }}
                />
              </div>
            )}
          </div>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
