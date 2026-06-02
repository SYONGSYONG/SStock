import { useState } from "react";
import type { StrategyConfig, StrategyName } from "../types";

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

const STRATEGY_LABEL: Record<string, string> = {
  ma_cross: "이동평균 크로스",
  rsi: "RSI",
};

/** 전략 설정을 사람이 읽기 쉬운 문구로 변환한다. */
export function describeStrategy(strategy: string, params: Record<string, number>): string {
  if (strategy === "ma_cross") {
    return `이동평균 크로스 · 단기 ${params.short ?? "-"} / 장기 ${params.long ?? "-"}`;
  }
  if (strategy === "rsi") {
    return `RSI · 기간 ${params.period ?? "-"} · 과매도 ${params.low ?? "-"} / 과매수 ${params.high ?? "-"}`;
  }
  return STRATEGY_LABEL[strategy] ?? strategy;
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
        <select
          aria-label="전략 선택"
          value={strategy}
          onChange={(e) => setStrategy(e.target.value as StrategyName)}
        >
          <option value="ma_cross">이동평균 크로스</option>
          <option value="rsi">RSI</option>
        </select>
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
