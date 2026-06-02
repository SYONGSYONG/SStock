import type { TradingMode } from "../types";

interface ModeBannerProps {
  mode: TradingMode;
  marketRunning: boolean;
  connected: boolean;
}

export function ModeBanner({ mode, marketRunning, connected }: ModeBannerProps) {
  const isLive = mode === "live";
  return (
    <header className={`mode-banner ${isLive ? "live" : "paper"}`}>
      <strong className="mode-label">
        {isLive ? "⚠ LIVE · 실전투자" : "PAPER · 모의투자"}
      </strong>
      <span className="spacer" />
      <span className={`pill ${marketRunning ? "on" : "off"}`}>
        봇 {marketRunning ? "● ON" : "○ OFF"}
      </span>
      <span className={`pill ${connected ? "on" : "off"}`}>
        실시간 {connected ? "연결됨" : "끊김"}
      </span>
    </header>
  );
}
