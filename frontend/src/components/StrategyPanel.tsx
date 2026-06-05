import { useEffect, useState } from "react";
import type { Budget, StrategyConfig, StrategyName, WatchItem } from "../types";
import { fmt } from "../lib/format";
import {
  describeStrategy,
  explainParams,
  getStrategyHelp,
  matchPreset,
  presetsFor,
  type StrategyPreset,
  STRATEGY_COMPARISON,
  STRATEGY_DEFAULTS,
  STRATEGY_LABEL,
  STRATEGY_PARAM_FIELDS,
  validateParams,
} from "../lib/strategy";
import { HelpPopover } from "./HelpPopover";
import { Modal } from "./Modal";

interface StrategyPanelProps {
  configs: StrategyConfig[];
  /** 종목별 자본 칸막이 현황(전략 항목 아래 가용/한도 표기용) */
  budgets: Budget[];
  /** 오토모드: 종목별 현재 시장 국면({종목코드: 국면키}). 추천 프리셋 표시용. */
  regimes?: Record<string, string>;
  /** 관심종목(종목코드→종목명 표시용) */
  items?: WatchItem[];
  /** 외부(실시간 시세 클릭)에서 종목코드를 채워넣을 때. n이 바뀌면 value로 설정. */
  presetSymbol?: { value: string; n: number };
  onAdd: (body: {
    symbol: string;
    strategy: StrategyName;
    params: Record<string, number>;
    enabled: boolean;
  }) => void;
  /** 전략과 함께 등록할/수정할 자본 칸막이(원금) 설정 */
  onSetBudget: (symbol: string, principal: number) => void;
  onToggle: (id: number, enabled: boolean) => void;
  onRemove: (id: number) => void;
  /** 전략 수정 저장. 전략 종류가 바뀌면 기존 전략을 지우고 새 전략으로 교체한다.
   *  미전달 시 onAdd로 폴백(같은 종류 파라미터만 upsert). */
  onEditStrategy?: (
    oldId: number,
    body: {
      symbol: string;
      strategy: StrategyName;
      params: Record<string, number>;
      enabled: boolean;
    },
  ) => void;
  /** 계좌 주문가능현금(원금 입력 아래 설정가능액 표시용) */
  orderableCash?: number | null;
  error?: string | null;
  /** 자본 칸막이 설정 오류 */
  budgetError?: string | null;
}

/** 전략 파라미터 입력 필드(추가 폼·수정 모달 공용). */
function StrategyParamInputs({
  strategy,
  params,
  onChange,
}: {
  strategy: StrategyName;
  params: Record<string, number>;
  onChange: (key: string, raw: string) => void;
}) {
  const fields = STRATEGY_PARAM_FIELDS[strategy] ?? [];
  return (
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
            onChange={(e) => onChange(f.key, e.target.value)}
          />
          <span className="param-default">기본 {STRATEGY_DEFAULTS[strategy][f.key]}</span>
        </label>
      ))}
    </div>
  );
}

/** 이동평균 크로스 vs RSI + MA 필터 비교표 */
function StrategyCompareTable() {
  return (
    <table className="strategy-compare">
      <thead>
        <tr>
          <th>구분</th>
          <th>이동평균 크로스</th>
          <th>RSI + MA 필터</th>
        </tr>
      </thead>
      <tbody>
        {STRATEGY_COMPARISON.map((row) => (
          <tr key={row.label}>
            <th>{row.label}</th>
            <td>{row.ma_cross}</td>
            <td>{row.rsi_ma}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
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

      {help.examples?.length > 0 && (
        <>
          <p className="help-section">예시 (상황)</p>
          <ul className="help-rules help-examples">
            {help.examples.map((ex) => (
              <li key={ex}>{ex}</li>
            ))}
          </ul>
        </>
      )}

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

const toNumber = (raw: string): number => (raw === "" ? Number.NaN : Number(raw));

const TEN_MILLION = 10_000_000;
const ONE_MILLION = 1_000_000;

/** 원금 입력 보조: 천만/백만 단위 ± 버튼.
 *  0 미만으로는 내려가지 않고, 증가(+) 시 max(설정가능금액)를 넘으면 max로 고정한다. */
function AmountSteppers({
  value,
  onChange,
  max,
}: {
  value: string;
  onChange: (next: string) => void;
  max?: number | null;
}) {
  const adjust = (delta: number) => {
    const current = Number(value) || 0;
    let next = current + delta;
    // 증가할 때만 상한 적용(감소는 그대로 줄이고 0에서 멈춤)
    if (delta > 0 && max != null && next > max) next = max;
    onChange(String(Math.max(0, next)));
  };
  return (
    <div className="amount-steppers">
      <button type="button" className="step-plus" onClick={() => adjust(TEN_MILLION)}>
        +천만
      </button>
      <button type="button" className="step-plus" onClick={() => adjust(ONE_MILLION)}>
        +백만
      </button>
      <button type="button" className="step-minus" onClick={() => adjust(-ONE_MILLION)}>
        −백만
      </button>
      <button type="button" className="step-minus" onClick={() => adjust(-TEN_MILLION)}>
        −천만
      </button>
      <button type="button" className="step-reset" onClick={() => onChange("")}>
        초기화
      </button>
    </div>
  );
}

export function StrategyPanel({
  configs,
  budgets,
  regimes = {},
  items = [],
  presetSymbol,
  onAdd,
  onSetBudget,
  onToggle,
  onRemove,
  onEditStrategy,
  orderableCash,
  error,
  budgetError,
}: StrategyPanelProps) {
  const [symbol, setSymbol] = useState("");

  // 실시간 시세에서 종목코드를 클릭하면 폼에 채운다(presetSymbol.n 변화 감지).
  useEffect(() => {
    if (presetSymbol && presetSymbol.value) setSymbol(presetSymbol.value);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presetSymbol?.n]);

  // 종목코드 → 종목명(관심종목·등록된 전략에서 해석)
  const nameOf = (sym: string) =>
    items.find((it) => it.symbol === sym)?.name ??
    configs.find((c) => c.symbol === sym)?.name ??
    "";
  // 기본 전략은 실전 권장(검토 문서)인 RSI + MA 필터를 먼저 띄운다.
  const [strategy, setStrategy] = useState<StrategyName>("rsi_ma");
  // ma_cross 프리셋 선택("" = 직접 설정). 누르면 해당 파라미터를 폼에 채운다.
  const [preset, setPreset] = useState("");
  // 선택 전략의 기본값으로 채워둔 편집 가능한 파라미터
  const [params, setParams] = useState<Record<string, number>>({
    ...STRATEGY_DEFAULTS.rsi_ma,
  });
  // 전략과 함께 등록할 자본 칸막이 원금
  const [principal, setPrincipal] = useState("");

  // 전략 수정 모달(파라미터 + 전략 종류 변경)
  const [editing, setEditing] = useState<StrategyConfig | null>(null);
  const [editStrategy, setEditStrategy] = useState<StrategyName>("ma_cross");
  const [editParams, setEditParams] = useState<Record<string, number>>({});
  // 수정 모달의 ma_cross 프리셋 선택("" = 직접 설정)
  const [editPreset, setEditPreset] = useState("");
  // 자본 칸막이(원금) 수정 모달
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [editPrincipal, setEditPrincipal] = useState("");
  // 전략 비교 팝업
  const [compareOpen, setCompareOpen] = useState(false);

  const budgetOf = (sym: string) => budgets.find((b) => b.symbol === sym) ?? null;

  const validSymbol = /^\d{6}$/.test(symbol);
  const paramError = validateParams(strategy, params);
  const principalValue = Number(principal);
  const validPrincipal = /^\d+$/.test(principal) && principalValue >= 1;

  // 설정가능금액 = 주문가능현금 − Σ(각 칸막이 가용액)
  const committed = budgets.reduce((sum, b) => sum + b.available, 0);
  const settable = orderableCash == null ? null : orderableCash - committed;

  const changeStrategy = (next: StrategyName) => {
    setStrategy(next);
    setParams({ ...STRATEGY_DEFAULTS[next] });
    setPreset(""); // 전략을 바꾸면 프리셋은 '직접 설정'으로 초기화
  };

  // 프리셋 선택 시 해당 파라미터로 폼을 채운다("" = 직접 설정 → 기본값).
  const changePreset = (key: string) => {
    setPreset(key);
    const p = presetsFor(strategy).find((x) => x.key === key);
    setParams(p ? { ...p.params } : { ...STRATEGY_DEFAULTS[strategy] });
  };
  const presetPurpose = presetsFor(strategy).find((x) => x.key === preset)?.purpose ?? "";

  const changeParam = (key: string, raw: string) => {
    setParams((prev) => ({ ...prev, [key]: toNumber(raw) }));
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validSymbol || paramError || !validPrincipal) return;
    // 전략과 자본 칸막이는 한 쌍으로만 의미가 있으므로 함께 등록한다.
    const ok = window.confirm(
      `${symbol} 종목에 전략과 자본 칸막이를 함께 등록합니다.\n` +
        `· 전략: ${describeStrategy(strategy, params)}\n` +
        `· 원금: ${principalValue.toLocaleString("ko-KR")}원\n\n` +
        `전략은 OFF 상태로 추가됩니다. 계속하시겠습니까?`,
    );
    if (!ok) return;
    onAdd({ symbol, strategy, params, enabled: false });
    onSetBudget(symbol, Math.floor(principalValue));
    setSymbol("");
    // 같은 프리셋으로 다른 종목에 연속 등록할 수 있게 프리셋·파라미터는 유지한다.
    const cur = presetsFor(strategy).find((x) => x.key === preset);
    setParams(cur ? { ...cur.params } : { ...STRATEGY_DEFAULTS[strategy] });
    setPrincipal("");
  };

  const openEdit = (c: StrategyConfig) => {
    setEditing(c);
    setEditStrategy(c.strategy);
    setEditParams({ ...c.params });
    setEditPreset(""); // 기존 파라미터가 어느 프리셋인지 알 수 없으므로 '직접 설정'
  };

  // 수정 모달에서 전략 종류를 바꾸면 그 전략의 기본 파라미터로 채운다.
  const changeEditStrategy = (next: StrategyName) => {
    setEditStrategy(next);
    setEditParams({ ...STRATEGY_DEFAULTS[next] });
    setEditPreset("");
  };

  // 수정 모달 프리셋 선택 시 해당 파라미터로 채운다("" = 직접 설정 → 기본값).
  const changeEditPreset = (key: string) => {
    setEditPreset(key);
    const p = presetsFor(editStrategy).find((x) => x.key === key);
    setEditParams(p ? { ...p.params } : { ...STRATEGY_DEFAULTS[editStrategy] });
  };
  const editPresetPurpose = presetsFor(editStrategy).find((x) => x.key === editPreset)?.purpose ?? "";

  const changeEditParam = (key: string, raw: string) => {
    setEditParams((prev) => ({ ...prev, [key]: toNumber(raw) }));
  };

  const editError = editing ? validateParams(editStrategy, editParams) : null;

  const saveEdit = () => {
    if (!editing || editError) return;
    const body = {
      symbol: editing.symbol,
      strategy: editStrategy,
      params: editParams,
      enabled: editing.enabled,
    };
    // 전략 종류가 바뀌면 기존 전략을 지우고 교체해야 하므로 onEditStrategy로 처리한다.
    // 미전달(구버전 호출부)이면 같은 종류 파라미터 upsert로 폴백한다.
    if (onEditStrategy) {
      onEditStrategy(editing.id, body);
    } else {
      onAdd(body);
    }
    setEditing(null);
  };

  // 오토모드 추천 프리셋 적용(사람 확인형) — 현재 파라미터를 프리셋으로 덮어쓴다.
  const applyRecommendedPreset = (c: StrategyConfig, preset: StrategyPreset) => {
    const ok = window.confirm(
      `${c.symbol} 전략에 추천 프리셋 '${preset.label}'을(를) 적용합니다.\n` +
        `· ${preset.purpose}\n\n현재 파라미터를 덮어씁니다. 계속하시겠습니까?`,
    );
    if (!ok) return;
    const body = {
      symbol: c.symbol,
      strategy: c.strategy,
      params: { ...preset.params },
      enabled: c.enabled,
    };
    if (onEditStrategy) onEditStrategy(c.id, body);
    else onAdd(body);
  };

  const openEditBudget = (b: Budget) => {
    setEditingBudget(b);
    setEditPrincipal(String(b.principal));
  };

  const editPrincipalValue = Number(editPrincipal);
  const editBudgetValid = /^\d+$/.test(editPrincipal) && editPrincipalValue >= 1;

  const saveEditBudget = () => {
    if (!editingBudget || !editBudgetValid) return;
    onSetBudget(editingBudget.symbol, Math.floor(editPrincipalValue));
    setEditingBudget(null);
  };

  // 활성화(ON) 인터락: 실수 방지를 위해 설정값을 팝업으로 확인한 뒤에만 켠다.
  // 끄기(OFF)는 즉시 적용. 체크박스는 c.enabled로 제어되므로 취소 시 자동으로 OFF 유지.
  const handleToggle = (c: StrategyConfig, checked: boolean) => {
    if (!checked) {
      onToggle(c.id, false);
      return;
    }
    const ok = window.confirm(
      `'${c.symbol} ${c.name ?? ""}' 전략을 활성화합니다.\n` +
        `${describeStrategy(c.strategy, c.params)}\n\n` +
        `이 설정으로 자동매매 신호 생성을 시작하시겠습니까?`,
    );
    if (!ok) return;
    onToggle(c.id, true);
  };

  return (
    <div className="panel-section">
      <div className="panel-head">
        <h2>전략</h2>
        <HelpPopover label={`${STRATEGY_LABEL[strategy]} 도움말`}>
          <StrategyHelpBody strategy={strategy} params={params} />
        </HelpPopover>
        <button type="button" className="link-action" onClick={() => setCompareOpen(true)}>
          전략 비교
        </button>
        <select
          aria-label="전략 선택"
          className="strategy-head-select"
          value={strategy}
          onChange={(e) => changeStrategy(e.target.value as StrategyName)}
        >
          <option value="rsi_ma">RSI + MA 필터</option>
          <option value="ma_cross">이동평균 크로스</option>
        </select>
      </div>
      <form className="strategy-form" onSubmit={submit}>
        <div className="strategy-symbol-row">
          <input
            aria-label="전략 종목코드"
            placeholder="종목코드"
            value={symbol}
            maxLength={6}
            onChange={(e) => setSymbol(e.target.value.replace(/\D/g, ""))}
          />
          {validSymbol && nameOf(symbol) && (
            <span className="symbol-name">{nameOf(symbol)}</span>
          )}
        </div>

        {presetsFor(strategy).length > 0 && (
          <label className="param-field preset-field">
            <span className="param-label">프리셋</span>
            <select
              aria-label="프리셋 선택"
              value={preset}
              onChange={(e) => changePreset(e.target.value)}
            >
              <option value="">(직접 설정)</option>
              {presetsFor(strategy).map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
            <span className="param-default">
              {presetPurpose || "상황별 추천 파라미터를 한 번에 채웁니다"}
            </span>
          </label>
        )}

        <StrategyParamInputs strategy={strategy} params={params} onChange={changeParam} />

        <label className="param-field budget-field">
          <span className="param-label">자본 칸막이 원금(원)</span>
          <input
            aria-label="자본 칸막이 원금"
            inputMode="numeric"
            placeholder="예: 1,000,000"
            value={principal ? Number(principal).toLocaleString("ko-KR") : ""}
            onChange={(e) => setPrincipal(e.target.value.replace(/\D/g, ""))}
          />
          <AmountSteppers value={principal} onChange={setPrincipal} max={settable} />
          <span className="param-default">전략과 함께 등록됩니다</span>
        </label>

        <p className="budget-rule">종목별 투입 원금 한도 (한도 = 원금, 실현손실은 차감 · 이익은 미반영)</p>
        <p className="budget-cash">
          {orderableCash == null ? (
            <span className="muted">주문가능현금 조회 불가</span>
          ) : (
            <>
              주문가능현금 {fmt(orderableCash)}원
              <br />
              칸막이 합계 {fmt(committed)}원 · 설정가능{" "}
              <b className={settable != null && settable < 0 ? "down" : "up"}>{fmt(settable)}</b>원
              {settable != null && settable < 0 && (
                <span className="down"> (칸막이 합계가 현금 초과)</span>
              )}
            </>
          )}
        </p>

        {paramError && validSymbol && <p className="error param-error">{paramError}</p>}
        {budgetError && <p className="error param-error">{budgetError}</p>}

        <button
          type="submit"
          className="strategy-add"
          disabled={!validSymbol || !!paramError || !validPrincipal}
        >
          추가
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      <ul className="strategy-list">
        {configs.map((c) => (
          <li key={c.id} className="strategy-item">
            <div className="strategy-head">
              <span className="code">{c.symbol}</span>
              <span className="name">{c.name ?? ""}</span>
              {(() => {
                const preset = matchPreset(c.strategy, c.params);
                return preset ? (
                  <span className="preset-badge" title={preset.purpose}>
                    {preset.label}
                  </span>
                ) : null;
              })()}
              <span className="spacer" />
              <label className="switch" title={c.enabled ? "전략 ON" : "전략 OFF"}>
                <input
                  type="checkbox"
                  checked={c.enabled}
                  onChange={(e) => handleToggle(c, e.target.checked)}
                />
                <span className="switch-track">
                  <span className="switch-knob" />
                </span>
                <span className="switch-label">{c.enabled ? "ON" : "OFF"}</span>
              </label>
              <button className="link-danger" onClick={() => onRemove(c.id)}>
                삭제
              </button>
            </div>
            <div className="strategy-desc">
              {describeStrategy(c.strategy, c.params)}
              <button className="link-action strategy-edit" onClick={() => openEdit(c)}>
                전략 수정
              </button>
            </div>
            {(() => {
              const regime = regimes[c.symbol];
              if (!regime) return null;
              const isUpRegime = regime === "강한상승" || regime === "아주강한상승";
              // 정책 A: 기본 추천 전략은 RSI+MA. ma_cross가 약한 횡보·하강 국면에선
              // RSI+MA 전환을 권장만 한다(전환은 '전략 수정'에서 사용자가 직접).
              if (c.strategy === "ma_cross" && !isUpRegime) {
                return (
                  <div
                    className="strategy-reco strategy-reco-hint"
                    title="추세추종에 불리한 국면 — RSI+MA 필터 권장"
                  >
                    <span className="reco-tag">권장</span>이 국면엔 <b>RSI + MA 필터</b>{" "}
                    <span className="reco-note">(전략 수정에서 변경)</span>
                  </div>
                );
              }
              // 국면에 맞는 프리셋 추천(현재 파라미터가 아직 그 프리셋이 아니면 적용 제안)
              const rec = presetsFor(c.strategy).find((p) => p.key === regime);
              if (!rec) return null;
              if (matchPreset(c.strategy, c.params)?.key === rec.key) return null;
              return (
                <div className="strategy-reco" title={rec.purpose}>
                  <span className="reco-tag">추천</span>
                  <b>{rec.label}</b>
                  <button
                    className="link-action reco-apply"
                    onClick={() => applyRecommendedPreset(c, rec)}
                  >
                    적용
                  </button>
                </div>
              );
            })()}
            {(() => {
              const b = budgetOf(c.symbol);
              if (!b) {
                return <div className="strategy-budget muted">자본 칸막이 미설정</div>;
              }
              return (
                <div className="strategy-budget">
                  가용 <b className={b.available < 0 ? "down" : undefined}>{fmt(b.available)}</b> /
                  한도 {fmt(b.ceiling)}원
                  {b.realized_pnl !== 0 && (
                    <span className={b.realized_pnl > 0 ? "up" : "down"}>
                      {" "}
                      (실현 {b.realized_pnl > 0 ? "+" : ""}
                      {fmt(b.realized_pnl)})
                    </span>
                  )}
                  <button className="link-action budget-edit" onClick={() => openEditBudget(b)}>
                    칸막이 수정
                  </button>
                </div>
              );
            })()}
          </li>
        ))}
        {configs.length === 0 && <li className="empty">등록된 전략이 없습니다</li>}
      </ul>

      {editing && (
        <Modal
          title={`${editing.symbol} ${editing.name ?? ""} 전략 수정`}
          onClose={() => setEditing(null)}
          dismissable={false}
        >
          <label className="param-field edit-strategy-field">
            <span className="param-label">전략 종류</span>
            <select
              aria-label="수정 전략 선택"
              value={editStrategy}
              onChange={(e) => changeEditStrategy(e.target.value as StrategyName)}
            >
              <option value="rsi_ma">RSI + MA 필터</option>
              <option value="ma_cross">이동평균 크로스</option>
            </select>
          </label>
          {editStrategy !== editing.strategy && (
            <p className="param-default edit-strategy-note">
              {STRATEGY_LABEL[editing.strategy]} → {STRATEGY_LABEL[editStrategy]}로 교체됩니다
              (파라미터는 기본값으로 초기화).
            </p>
          )}
          {presetsFor(editStrategy).length > 0 && (
            <label className="param-field preset-field">
              <span className="param-label">프리셋</span>
              <select
                aria-label="수정 프리셋 선택"
                value={editPreset}
                onChange={(e) => changeEditPreset(e.target.value)}
              >
                <option value="">(직접 설정)</option>
                {presetsFor(editStrategy).map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
              <span className="param-default">
                {editPresetPurpose || "프리셋을 고르면 파라미터가 채워집니다(이후 수정 가능)"}
              </span>
            </label>
          )}
          <StrategyParamInputs
            strategy={editStrategy}
            params={editParams}
            onChange={changeEditParam}
          />
          {editError && <p className="error param-error">{editError}</p>}
          <div className="edit-modal-actions">
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>
              취소
            </button>
            <button type="button" className="strategy-add" disabled={!!editError} onClick={saveEdit}>
              저장
            </button>
          </div>
        </Modal>
      )}

      {editingBudget && (() => {
        // 수정 시 상한 = 설정가능 + 이 칸막이의 현재 원금.
        // (settable은 모든 칸막이의 가용액을 이미 차감했으므로, 이 종목 몫을 되돌려
        //  더해 주면 실현손익·보유원가 항이 상쇄되어 순수 원금 상한으로 떨어진다.)
        const editSettable =
          settable == null ? null : settable + editingBudget.principal;
        const overEdit =
          editSettable != null && editPrincipalValue > editSettable;
        return (
        <Modal
          title={`${editingBudget.symbol} · 자본 칸막이 원금 수정`}
          onClose={() => setEditingBudget(null)}
          dismissable={false}
        >
          <label className="param-field">
            <span className="param-label">원금(원)</span>
            <input
              type="text"
              aria-label="칸막이 수정 원금"
              inputMode="numeric"
              value={editPrincipal ? Number(editPrincipal).toLocaleString("ko-KR") : ""}
              onChange={(e) => setEditPrincipal(e.target.value.replace(/\D/g, ""))}
            />
            <AmountSteppers value={editPrincipal} onChange={setEditPrincipal} max={editSettable} />
            <span className="param-default">현재 {fmt(editingBudget.principal)}원</span>
          </label>
          {editSettable != null && (
            <p className="budget-cash">
              설정가능{" "}
              <b className={overEdit ? "down" : "up"}>{fmt(editSettable)}</b>원
              {overEdit && <span className="down"> (주문가능현금 초과)</span>}
            </p>
          )}
          <div className="edit-modal-actions">
            <button type="button" className="btn-ghost" onClick={() => setEditingBudget(null)}>
              취소
            </button>
            <button
              type="button"
              className="strategy-add"
              disabled={!editBudgetValid}
              onClick={saveEditBudget}
            >
              저장
            </button>
          </div>
        </Modal>
        );
      })()}

      {compareOpen && (
        <Modal title="전략 비교 — 이동평균 크로스 vs RSI + MA 필터" onClose={() => setCompareOpen(false)}>
          <StrategyCompareTable />
        </Modal>
      )}
    </div>
  );
}
