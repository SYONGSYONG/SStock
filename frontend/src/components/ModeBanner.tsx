import type { ReactNode } from "react";
import type { TradingMode } from "../types";

interface ModeBannerProps {
  viewMode: TradingMode;
  onSwitchMode: (mode: TradingMode) => void;
  paperBotRunning: boolean;
  liveBotRunning: boolean;
  connected: boolean;
  /** 우측 봇 상태 pill 왼쪽에 들어갈 컨트롤(자동매매 봇/시세 수집 컴팩트 버튼) */
  controls?: ReactNode;
}

export function ModeBanner({
  viewMode,
  onSwitchMode,
  paperBotRunning,
  liveBotRunning,
  connected,
  controls,
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
      {controls && <div className="banner-controls">{controls}</div>}
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
