import type { StrategyConfig, StrategyPerfRow } from "../types";
import { STRATEGY_LABEL, matchPreset } from "../lib/strategy";

interface StrategyPerformanceProps {
  rows: StrategyPerfRow[];
  /** 현재 전략 설정(프리셋 배지 추론용 — 신호 기반 보드엔 프리셋 정보가 없어 현재값으로 추론) */
  configs: StrategyConfig[];
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
 * ON·OFF(관찰) 전략 모두 표시되어 "어느 전략·프리셋이 실제로 더 나았나"를 비교한다.
 */
export function StrategyPerformance({ rows, configs }: StrategyPerformanceProps) {
  return (
    <section className="panel strategy-perf">
      <div className="strategy-perf-head">
        <h2>전략 성과 (섀도우)</h2>
        <span className="strategy-perf-note">
          매매신호 기반 가상 성과 · 완결 거래(매수→매도) 기준 · 실제 주문과 무관
        </span>
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
              <th className="num">보유중</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const cfg = configs.find(
                (c) => c.symbol === r.symbol && c.strategy === r.strategy,
              );
              const preset = cfg ? matchPreset(r.strategy, cfg.params) : null;
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
                  <td className="num">{r.trades}</td>
                  <td className="num">{r.trades > 0 ? `${r.win_rate.toFixed(0)}%` : "—"}</td>
                  <td className={`num ${rateClass(r.sum_return)}`}>
                    {r.trades > 0 ? signed(r.sum_return) : "—"}
                  </td>
                  <td className={`num ${rateClass(r.avg_return)}`}>
                    {r.trades > 0 ? signed(r.avg_return) : "—"}
                  </td>
                  <td className="num">{r.open_position > 0 ? `${r.open_position}` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
