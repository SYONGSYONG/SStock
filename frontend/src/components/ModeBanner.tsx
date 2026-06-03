import type { TradingMode } from "../types";

interface ModeBannerProps {
  viewMode: TradingMode;
  onSwitchMode: (mode: TradingMode) => void;
  paperBotRunning: boolean;
  liveBotRunning: boolean;
  connected: boolean;
}

export function ModeBanner({
  viewMode,
  onSwitchMode,
  paperBotRunning,
  liveBotRunning,
  connected,
}: ModeBannerProps) {
  const isLive = viewMode === "live";

  return (
    <header className={`mode-banner ${isLive ? "live" : "paper"}`}>
      {isLive && (
        <span className="live-warning">⚠ 실전투자 — 실제 주문이 체결됩니다</span>
      )}
      <div className="mode-toggle">
        <button
          className={`toggle-btn ${viewMode === "paper" ? "active" : ""}`}
          onClick={() => onSwitchMode("paper")}
        >
          모의
        </button>
        <button
          className={`toggle-btn ${viewMode === "live" ? "active" : ""}`}
          onClick={() => onSwitchMode("live")}
        >
          실전
        </button>
      </div>
      <span className="spacer" />
      <span className={`pill ${paperBotRunning ? "on" : "off"}`}>
        모의 봇 {paperBotRunning ? "●" : "○"}
      </span>
      <span className={`pill ${liveBotRunning ? "on" : "off"}`}>
        실전 봇 {liveBotRunning ? "●" : "○"}
      </span>
      <span className={`pill ${connected ? "on" : "off"}`}>
        실시간 {connected ? "연결됨" : "끊김"}
      </span>
    </header>
  );
}
