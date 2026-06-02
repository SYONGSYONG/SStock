// 전략 식별자 → 사람이 읽는 라벨 (전략 패널 / 매매 신호 공통)
export const STRATEGY_LABEL: Record<string, string> = {
  ma_cross: "이동평균 크로스",
  rsi: "RSI",
};

export function strategyLabel(strategy: string): string {
  return STRATEGY_LABEL[strategy] ?? strategy;
}

/** 전략 + 파라미터를 한 줄 설명으로 변환한다. */
export function describeStrategy(strategy: string, params: Record<string, number>): string {
  if (strategy === "ma_cross") {
    return `이동평균 크로스 · 단기 ${params.short ?? "-"} / 장기 ${params.long ?? "-"}`;
  }
  if (strategy === "rsi") {
    return `RSI · 기간 ${params.period ?? "-"} · 과매도 ${params.low ?? "-"} / 과매수 ${params.high ?? "-"}`;
  }
  return strategyLabel(strategy);
}
