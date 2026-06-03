import { useState } from "react";
import type { StrategyConfig, StrategyName } from "../types";
import { describeStrategy, getStrategyHelp } from "../lib/strategy";
import { HelpPopover } from "./HelpPopover";

interface StrategyPanelProps {
  configs: StrategyConfig[];
  onAdd: (body: {
    symbol: string;
    strategy: StrategyName;
    params: Record<string, number>;
    enabled: boolean;
  }) => void;
  onToggle: (id: number, enabled: boolean) => void;
  onRemove: (id: number) => void;
  error?: string | null;
}

const DEFAULT_PARAMS: Record<StrategyName, Record<string, number>> = {
  ma_cross: { short: 5, long: 20 },
  rsi: { period: 14, low: 30, high: 70 },
};

/** 선택된 전략의 도움말 본문 */
function StrategyHelpBody({ strategy }: { strategy: StrategyName }) {
  const help = getStrategyHelp(strategy);
  if (!help) return null;
  return (
    <>
      <strong className="help-title">{help.title}</strong>
      <p className="help-summary">{help.summary}</p>
      <ul className="help-rules">
        {help.rules.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      <p className="help-note">⚠ {help.note}</p>
    </>
  );
}

export function StrategyPanel({ configs, onAdd, onToggle, onRemove, error }: StrategyPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState<StrategyName>("ma_cross");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(symbol)) return;
    onAdd({ symbol, strategy, params: DEFAULT_PARAMS[strategy], enabled: false });
    setSymbol("");
  };

  return (
    <section className="panel">
      <h2>전략</h2>
      <form className="watch-form" onSubmit={submit}>
        <input
          aria-label="전략 종목코드"
          placeholder="종목코드"
          value={symbol}
          maxLength={6}
          onChange={(e) => setSymbol(e.target.value.replace(/\D/g, ""))}
        />
        <div className="strategy-pick">
          <select
            aria-label="전략 선택"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as StrategyName)}
          >
            <option value="ma_cross">이동평균 크로스</option>
            <option value="rsi">RSI</option>
          </select>
          <HelpPopover label={`${strategy === "rsi" ? "RSI" : "이동평균 크로스"} 도움말`}>
            <StrategyHelpBody strategy={strategy} />
          </HelpPopover>
        </div>
        <button type="submit" disabled={!/^\d{6}$/.test(symbol)}>
          추가
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul className="strategy-list">
        {configs.map((c) => (
          <li key={c.id} className="strategy-item">
            <div className="strategy-head">
              <span className="code">{c.symbol}</span>
              <span className="spacer" />
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={c.enabled}
                  onChange={(e) => onToggle(c.id, e.target.checked)}
                />
                {c.enabled ? "ON" : "OFF"}
              </label>
              <button className="link-danger" onClick={() => onRemove(c.id)}>
                삭제
              </button>
            </div>
            <div className="strategy-desc">{describeStrategy(c.strategy, c.params)}</div>
          </li>
        ))}
        {configs.length === 0 && <li className="empty">등록된 전략이 없습니다</li>}
      </ul>
    </section>
  );
}
