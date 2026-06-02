import { useState } from "react";
import type { TradingMode } from "../types";

interface BotControlProps {
  running: boolean;
  mode: TradingMode;
  onStart: (confirmLive: boolean) => void;
  onStop: () => void;
  error?: string | null;
}

export function BotControl({ running, mode, onStart, onStop, error }: BotControlProps) {
  const isLive = mode === "live";
  const [confirming, setConfirming] = useState(false);

  const handleStart = () => {
    if (isLive && !confirming) {
      setConfirming(true);
      return;
    }
    onStart(isLive);
    setConfirming(false);
  };

  return (
    <section className="panel">
      <h2>자동매매 봇</h2>
      {running ? (
        <button className="btn-stop" onClick={onStop}>
          봇 정지
        </button>
      ) : confirming ? (
        <div className="confirm-box">
          <p className="error">⚠ 실전(LIVE) 자동매매를 시작합니다. 실제 주문이 집행됩니다.</p>
          <button className="btn-stop" onClick={handleStart}>
            실전 시작 확인
          </button>
          <button className="link-danger" onClick={() => setConfirming(false)}>
            취소
          </button>
        </div>
      ) : (
        <button className={isLive ? "btn-stop" : "btn-start"} onClick={handleStart}>
          {isLive ? "봇 시작 (실전)" : "봇 시작"}
        </button>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
