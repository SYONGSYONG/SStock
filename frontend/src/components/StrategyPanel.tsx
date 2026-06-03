import { useState } from "react";
import type { StrategyConfig, StrategyName } from "../types";
import {
  describeStrategy,
  explainParams,
  getStrategyHelp,
  STRATEGY_DEFAULTS,
  STRATEGY_LABEL,
  STRATEGY_PARAM_FIELDS,
  validateParams,
} from "../lib/strategy";
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

/** 선택된 전략의 도움말 본문 */
function StrategyHelpBody({
  strategy,
  params,
}: {
  strategy: StrategyName;
  params: Record<string, number>;
}) {
  const help = getStrategyHelp(strategy);
  if (!help) return null;
  const meanings = explainParams(strategy, params);
  return (
    <>
      <strong className="help-title">{help.title}</strong>
      <p className="help-summary">{help.summary}</p>

      <p className="help-section">매매 규칙</p>
      <ul className="help-rules">
        {help.rules.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>

      {meanings.length > 0 && (
        <>
          <p className="help-section">설정값의 의미</p>
          <ul className="help-rules">
            {meanings.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </>
      )}

      <p className="help-note">⚠ {help.note}</p>
    </>
  );
}

export function StrategyPanel({ configs, onAdd, onToggle, onRemove, error }: StrategyPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState<StrategyName>("ma_cross");
  // 선택 전략의 기본값으로 채워둔 편집 가능한 파라미터
  const [params, setParams] = useState<Record<string, number>>({
    ...STRATEGY_DEFAULTS.ma_cross,
  });

  const fields = STRATEGY_PARAM_FIELDS[strategy] ?? [];
  const validSymbol = /^\d{6}$/.test(symbol);
  const paramError = validateParams(strategy, params);

  const changeStrategy = (next: StrategyName) => {
    setStrategy(next);
    // 전략을 바꾸면 해당 전략의 기본값으로 초기화
    setParams({ ...STRATEGY_DEFAULTS[next] });
  };

  const changeParam = (key: string, raw: string) => {
    // 빈 입력은 NaN으로 두어 검증에서 걸리게 한다(0으로 강제하지 않음).
    const value = raw === "" ? Number.NaN : Number(raw);
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validSymbol || paramError) return;
    // 추가 실수 방지를 위해 한 번 더 확인
    const ok = window.confirm(
      `${symbol} 종목에 '${STRATEGY_LABEL[strategy]}' 전략을 추가합니다.\n` +
        `${describeStrategy(strategy, params)}\n\n계속하시겠습니까?`,
    );
    if (!ok) return;
    onAdd({ symbol, strategy, params, enabled: false });
    setSymbol("");
    setParams({ ...STRATEGY_DEFAULTS[strategy] });
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>전략</h2>
        <HelpPopover label={`${STRATEGY_LABEL[strategy]} 도움말`}>
          <StrategyHelpBody strategy={strategy} params={params} />
        </HelpPopover>
      </div>
      <form className="strategy-form" onSubmit={submit}>
        <div className="strategy-form-row">
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
            onChange={(e) => changeStrategy(e.target.value as StrategyName)}
          >
            <option value="ma_cross">이동평균 크로스</option>
            <option value="rsi">RSI</option>
          </select>
        </div>

        <div className="strategy-params">
          {fields.map((f) => (
            <label key={f.key} className="param-field">
              <span className="param-label">{f.label}</span>
              <input
                type="number"
                aria-label={f.label}
                min={f.min}
                max={f.max}
                value={Number.isFinite(params[f.key]) ? params[f.key] : ""}
                onChange={(e) => changeParam(f.key, e.target.value)}
              />
              <span className="param-default">기본 {STRATEGY_DEFAULTS[strategy][f.key]}</span>
            </label>
          ))}
        </div>

        {paramError && validSymbol && <p className="error param-error">{paramError}</p>}

        <button type="submit" className="strategy-add" disabled={!validSymbol || !!paramError}>
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
