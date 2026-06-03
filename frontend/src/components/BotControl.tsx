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

  const handleStart = () => {
    if (isLive) {
      // 실전 모드: 실돈 매매라 시작 전 명시적 확인을 받는다(안전 게이트).
      const ok = window.confirm(
        "실전투자 봇을 시작합니다.\n실제 계좌에서 주문이 체결됩니다. 계속하시겠습니까?",
      );
      if (!ok) return;
      onStart(true);
    } else {
      // 모의 모드: 바로 시작
      onStart(false);
    }
  };

  return (
    <section className="panel">
      <h2>자동매매 봇</h2>
      {running ? (
        <button className="btn-stop" onClick={onStop}>
          봇 정지
        </button>
      ) : (
        <button className={isLive ? "btn-stop" : "btn-start"} onClick={handleStart}>
          {isLive ? "봇 시작 (실전)" : "봇 시작"}
        </button>
      )}
      {isLive && !running && (
        <p className="muted" style={{ marginTop: "8px", fontSize: "12px" }}>
          버튼을 클릭하면 실제 주문이 체결됩니다.
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
