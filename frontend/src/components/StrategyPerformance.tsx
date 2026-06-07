import type { Quote, StrategyConfig, StrategyPerfRow } from "../types";
import { STRATEGY_LABEL, matchPreset } from "../lib/strategy";

/** 완결 거래가 이 미만이면 표본 부족으로 보고 경고/흐림 처리(성과를 실력으로 오인 방지). */
export const MIN_RELIABLE_TRADES = 5;

export type PerfPeriod = "all" | "today" | "3d" | "7d";

export const PERF_PERIODS: { key: PerfPeriod; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "today", label: "오늘" },
  { key: "3d", label: "최근 3일" },
  { key: "7d", label: "최근 7일" },
];

/** 기간 선택값 → API `start`(KST 날짜). 전체면 undefined. 브라우저 로컬(KST) 기준. */
export function perfPeriodStart(period: PerfPeriod): string | undefined {
  if (period === "all") return undefined;
  const days = period === "today" ? 0 : period === "3d" ? 2 : 6;
  const d = new Date();
  d.setDate(d.getDate() - days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

interface StrategyPerformanceProps {
  rows: StrategyPerfRow[];
  /** 현재 전략 설정(프리셋 배지 추론용 — 신호 기반 보드엔 프리셋 정보가 없어 현재값으로 추론) */
  configs: StrategyConfig[];
  /** 실시간 시세(미실현 평가용). 종목코드 → Quote */
  quotes: Record<string, Quote>;
  period: PerfPeriod;
  onPeriodChange: (period: PerfPeriod) => void;
}

/** 수익률(%) 부호에 따른 국내 관례 색상 클래스(이익=빨강 up, 손실=파랑 down). */
function rateClass(rate: number): string {
  if (rate > 0) return "up";
  if (rate < 0) return "down";
  return "neutral";
}

function signed(rate: number): string {
  const sign = rate > 0 ? "+" : "";
  return `${sign}${rate.toFixed(2)}%`;
}

/**
 * 섀도우 성과 보드 — 신호(`signals`)만으로 계산한 (종목,전략)별 가상 성과.
 * 완결 거래(BUY→SELL 페어)의 수익률을 집계한다. 실제 주문·전략 전환과 무관(위험 0).
 * 보강: 표본 부족 경고, 미실현 평가(실시간 시세 결합), 기간 필터.
 */
export function StrategyPerformance({
  rows,
  configs,
  quotes,
  period,
  onPeriodChange,
}: StrategyPerformanceProps) {
  return (
    <section className="panel strategy-perf">
      <div className="strategy-perf-head">
        <h2>전략 성과 (섀도우)</h2>
        <span className="strategy-perf-note">
          매매신호 기반 가상 성과 · 완결 거래(매수→매도) 기준 · 실제 주문과 무관
        </span>
        <div className="perf-period" role="group" aria-label="기간 필터">
          {PERF_PERIODS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`perf-period-btn${period === p.key ? " active" : ""}`}
              onClick={() => onPeriodChange(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="empty">아직 완결된 가상 거래가 없습니다(봇 가동 중 신호가 쌓이면 표시).</p>
      ) : (
        <table className="perf-table">
          <thead>
            <tr>
              <th>종목</th>
              <th>전략</th>
              <th className="num">완결</th>
              <th className="num">승률</th>
              <th className="num">누적 수익률</th>
              <th className="num">평균 수익률</th>
              <th className="num">미실현</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const cfg = configs.find(
                (c) => c.symbol === r.symbol && c.strategy === r.strategy,
              );
              const preset = cfg ? matchPreset(r.strategy, cfg.params) : null;
              const lowSample = r.trades > 0 && r.trades < MIN_RELIABLE_TRADES;
              const dim = lowSample ? " perf-dim" : "";

              // 미실현: 미청산 + 진입가 + 현재가가 모두 있을 때만 계산.
              const price = quotes[r.symbol]?.price ?? null;
              const canUnrealized =
                r.open_position > 0 && r.open_entry != null && price != null;
              const unrealized = canUnrealized
                ? ((price - r.open_entry!) / r.open_entry!) * 100
                : null;

              return (
                <tr key={`${r.symbol}:${r.strategy}`}>
                  <td>
                    <span className="perf-symbol-name">{r.name || r.symbol}</span>
                    <span className="perf-symbol-code">{r.symbol}</span>
                  </td>
                  <td>
                    {STRATEGY_LABEL[r.strategy] ?? r.strategy}
                    {preset && <span className="perf-preset-badge">{preset.label}</span>}
                  </td>
                  <td className="num">
                    {r.trades}
                    {lowSample && <span className="perf-lowsample">표본 부족</span>}
                  </td>
                  <td className="num">{r.trades > 0 ? `${r.win_rate.toFixed(0)}%` : "—"}</td>
                  <td className={`num ${rateClass(r.sum_return)}${dim}`}>
                    {r.trades > 0 ? signed(r.sum_return) : "—"}
                  </td>
                  <td className={`num ${rateClass(r.avg_return)}${dim}`}>
                    {r.trades > 0 ? signed(r.avg_return) : "—"}
                  </td>
                  <td className={`num ${unrealized != null ? rateClass(unrealized) : ""}`}>
                    {unrealized != null
                      ? signed(unrealized)
                      : r.open_position > 0
                        ? "보유"
                        : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
