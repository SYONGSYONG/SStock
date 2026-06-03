import { useState } from "react";
import type { Budget, StrategyConfig, StrategyName } from "../types";
import { fmt } from "../lib/format";
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
import { Modal } from "./Modal";

interface StrategyPanelProps {
  configs: StrategyConfig[];
  /** 종목별 자본 칸막이 현황(전략 항목 아래 가용/한도 표기용) */
  budgets: Budget[];
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

const toNumber = (raw: string): number => (raw === "" ? Number.NaN : Number(raw));

export function StrategyPanel({
  configs,
  budgets,
  onAdd,
  onSetBudget,
  onToggle,
  onRemove,
  orderableCash,
  error,
  budgetError,
}: StrategyPanelProps) {
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState<StrategyName>("ma_cross");
  // 선택 전략의 기본값으로 채워둔 편집 가능한 파라미터
  const [params, setParams] = useState<Record<string, number>>({
    ...STRATEGY_DEFAULTS.ma_cross,
  });
  // 전략과 함께 등록할 자본 칸막이 원금
  const [principal, setPrincipal] = useState("");

  // 전략 파라미터 수정 모달
  const [editing, setEditing] = useState<StrategyConfig | null>(null);
  const [editParams, setEditParams] = useState<Record<string, number>>({});
  // 자본 칸막이(원금) 수정 모달
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [editPrincipal, setEditPrincipal] = useState("");

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
  };

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
    setParams({ ...STRATEGY_DEFAULTS[strategy] });
    setPrincipal("");
  };

  const openEdit = (c: StrategyConfig) => {
    setEditing(c);
    setEditParams({ ...c.params });
  };

  const changeEditParam = (key: string, raw: string) => {
    setEditParams((prev) => ({ ...prev, [key]: toNumber(raw) }));
  };

  const editError = editing ? validateParams(editing.strategy, editParams) : null;

  const saveEdit = () => {
    if (!editing || editError) return;
    // 같은 종목·전략으로 upsert → 파라미터만 갱신(활성 상태 유지)
    onAdd({
      symbol: editing.symbol,
      strategy: editing.strategy,
      params: editParams,
      enabled: editing.enabled,
    });
    setEditing(null);
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

        <StrategyParamInputs strategy={strategy} params={params} onChange={changeParam} />

        <label className="param-field budget-field">
          <span className="param-label">자본 칸막이 원금(원)</span>
          <input
            aria-label="자본 칸막이 원금"
            inputMode="numeric"
            placeholder="예: 1000000"
            value={principal}
            onChange={(e) => setPrincipal(e.target.value.replace(/\D/g, ""))}
          />
          <span className="param-default">전략과 함께 등록됩니다</span>
        </label>

        <p className="budget-rule">종목별 투입 원금 한도 (한도 = 원금 + 실현손익)</p>
        <p className="budget-cash">
          {orderableCash == null ? (
            <span className="muted">주문가능현금 조회 불가</span>
          ) : (
            <>
              주문가능현금 {fmt(orderableCash)}원 · 설정가능{" "}
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
          title={`${editing.symbol} ${editing.name ?? ""} · ${STRATEGY_LABEL[editing.strategy]} 수정`}
          onClose={() => setEditing(null)}
        >
          <StrategyParamInputs
            strategy={editing.strategy}
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

      {editingBudget && (
        <Modal
          title={`${editingBudget.symbol} · 자본 칸막이 원금 수정`}
          onClose={() => setEditingBudget(null)}
        >
          <label className="param-field">
            <span className="param-label">원금(원)</span>
            <input
              type="text"
              aria-label="칸막이 수정 원금"
              inputMode="numeric"
              value={editPrincipal}
              onChange={(e) => setEditPrincipal(e.target.value.replace(/\D/g, ""))}
            />
            <span className="param-default">현재 {fmt(editingBudget.principal)}원</span>
          </label>
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
      )}
    </div>
  );
}
