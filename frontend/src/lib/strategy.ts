// 전략 식별자 → 사람이 읽는 라벨 (전략 패널 / 매매 신호 공통)
export const STRATEGY_LABEL: Record<string, string> = {
  ma_cross: "이동평균 크로스",
  rsi: "RSI",
};

export function strategyLabel(strategy: string): string {
  return STRATEGY_LABEL[strategy] ?? strategy;
}

/** 전략 도움말(팝오버용) 구조화 설명. */
export interface StrategyHelp {
  title: string;
  summary: string;
  rules: string[];
  note: string;
}

export const STRATEGY_HELP: Record<string, StrategyHelp> = {
  ma_cross: {
    title: "이동평균 크로스",
    summary: "단기·장기 이동평균선이 교차하는 순간 매매하는 추세추종 전략입니다.",
    rules: [
      "골든크로스(단기선이 장기선을 아래→위로 돌파) → 매수",
      "데드크로스(단기선이 장기선을 위→아래로 이탈) → 매도",
      "단기 N / 장기 M = 최근 N개·M개 시세의 평균선",
    ],
    note: "이 봇은 ‘일(日)’이 아니라 수신한 실시간 시세(틱) 단위로 계산합니다. 그래서 활발한 장에서는 신호가 잦고(특히 횡보장에선 매수·매도가 번갈아 나는 휩쏘), 강한 추세에서는 드뭅니다. 최소 (장기+1)개 시세가 쌓여야 평가가 시작되며, 봇을 재시작하면 다시 누적합니다.",
  },
  rsi: {
    title: "RSI (상대강도지수)",
    summary: "최근 기간의 상승/하락 강도를 0~100으로 나타내 과열·침체를 판단합니다.",
    rules: [
      "과매도선(low)을 아래→위로 돌파 → 매수",
      "과매수선(high)을 위→아래로 이탈 → 매도",
      "기간 = RSI 계산에 쓰는 시세 개수, 과매도/과매수 = 기준선",
    ],
    note: "이동평균 크로스와 동일하게 수신한 시세(틱) 단위로 계산합니다. 최소 (기간+2)개 시세가 쌓여야 평가가 시작됩니다.",
  },
};

export function getStrategyHelp(strategy: string): StrategyHelp | null {
  return STRATEGY_HELP[strategy] ?? null;
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
