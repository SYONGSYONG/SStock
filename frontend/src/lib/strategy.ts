// 전략 식별자 → 사람이 읽는 라벨 (전략 패널 / 매매 신호 공통)
export const STRATEGY_LABEL: Record<string, string> = {
  ma_cross: "이동평균 크로스",
  rsi: "RSI",
};

/** 전략별 기본 파라미터 값(단일 진실 공급원). */
export const STRATEGY_DEFAULTS: Record<string, Record<string, number>> = {
  ma_cross: { short: 5, long: 20 },
  rsi: { period: 14, low: 30, high: 70 },
};

/** 편집 가능한 파라미터 필드 정의(입력 라벨·범위). */
export interface ParamField {
  key: string;
  label: string;
  min: number;
  max: number;
}

export const STRATEGY_PARAM_FIELDS: Record<string, ParamField[]> = {
  ma_cross: [
    { key: "short", label: "단기", min: 1, max: 999 },
    { key: "long", label: "장기", min: 2, max: 999 },
  ],
  rsi: [
    { key: "period", label: "기간", min: 2, max: 999 },
    { key: "low", label: "과매도", min: 1, max: 99 },
    { key: "high", label: "과매수", min: 1, max: 99 },
  ],
};

/** 파라미터 유효성 검사. 통과하면 null, 위반하면 한국어 오류 메시지. */
export function validateParams(
  strategy: string,
  params: Record<string, number>,
): string | null {
  if (strategy === "ma_cross") {
    if (!Number.isFinite(params.short) || !Number.isFinite(params.long)) {
      return "단기·장기 값을 입력하세요";
    }
    if (params.short < 1 || params.long < 2) {
      return "단기는 1 이상, 장기는 2 이상이어야 합니다";
    }
    if (params.short >= params.long) {
      return "단기는 장기보다 작아야 합니다";
    }
  }
  if (strategy === "rsi") {
    const { period, low, high } = params;
    if (![period, low, high].every(Number.isFinite)) {
      return "기간·과매도·과매수 값을 입력하세요";
    }
    if (period < 2) {
      return "기간은 2 이상이어야 합니다";
    }
    if (!(low > 0 && low < high && high < 100)) {
      return "0 < 과매도 < 과매수 < 100 이어야 합니다";
    }
  }
  return null;
}

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
    summary:
      "‘이동평균선’은 최근 가격 여러 개의 평균을 이은 선으로, 들쭉날쭉한 가격을 부드럽게 펴서 흐름을 보여줍니다. 이 전략은 빠른 단기선과 느린 장기선, 두 평균선이 서로 교차(크로스)하는 순간을 ‘추세 전환’ 신호로 보고 매매하는 추세추종 전략입니다.",
    rules: [
      "골든크로스: 단기선이 장기선을 아래→위로 돌파 → 매수(상승 전환)",
      "데드크로스: 단기선이 장기선을 위→아래로 이탈 → 매도(하락 전환)",
      "두 선이 ‘교차하는 그 순간’에만 신호가 나며, 한쪽이 위에 머무는 동안에는 신호가 없습니다.",
    ],
    note: "중요 — 이 봇은 ‘일(日)’이 아니라 수신한 실시간 시세(틱) 단위로 평균을 냅니다. 즉 ‘5일선/20일선’이 아니라 ‘최근 5틱/20틱 평균선’이며, 활발한 장에서는 20틱이 수 초~수십 초에 불과해 일봉보다 훨씬 민감합니다. 그래서 횡보장에서는 매수·매도가 번갈아 잦게 나고(휩쏘), 강한 추세에서는 한 번 교차 후 한참 신호가 없습니다. 최소 (장기+1)개의 시세가 쌓여야 평가가 시작되고, 봇을 재시작하면 다시 0부터 누적합니다.",
  },
  rsi: {
    title: "RSI (상대강도지수)",
    summary:
      "RSI는 최근 일정 기간의 상승 폭과 하락 폭을 비교해 0~100 사이 값으로 ‘과열(많이 올랐다)’과 ‘침체(많이 내렸다)’를 나타내는 지표입니다. 보통 70 이상이면 과매수, 30 이하이면 과매도로 봅니다.",
    rules: [
      "과매도선(low)을 아래→위로 돌파 → 매수(바닥 탈출)",
      "과매수선(high)을 위→아래로 이탈 → 매도(고점 꺾임)",
      "단순히 구간 안에 있는 게 아니라 ‘경계선을 넘나드는 순간’에 신호가 납니다.",
    ],
    note: "이동평균 크로스와 동일하게 수신한 시세(틱) 단위로 계산합니다. 최소 (기간+2)개의 시세가 쌓여야 평가가 시작됩니다.",
  },
};

export function getStrategyHelp(strategy: string): StrategyHelp | null {
  return STRATEGY_HELP[strategy] ?? null;
}

/** 적용된 파라미터 값(예: 5/20)이 각각 무엇을 뜻하는지 풀어쓴다. */
export function explainParams(strategy: string, params: Record<string, number>): string[] {
  if (strategy === "ma_cross") {
    const short = params.short ?? "-";
    const long = params.long ?? "-";
    return [
      `단기 ${short} = 최근 ${short}개 시세의 평균선(MA${short}) — 빠르게 반응`,
      `장기 ${long} = 최근 ${long}개 시세의 평균선(MA${long}) — 느리게 반응(추세)`,
      `MA${short}가 MA${long}을 위로 뚫으면 매수, 아래로 뚫으면 매도`,
    ];
  }
  if (strategy === "rsi") {
    const period = params.period ?? "-";
    const low = params.low ?? "-";
    const high = params.high ?? "-";
    return [
      `기간 ${period} = 최근 ${period}개 시세로 상승/하락 강도 계산`,
      `과매도 ${low} = RSI가 이 값 아래로 갔다가 회복하면 매수`,
      `과매수 ${high} = RSI가 이 값 위로 갔다가 꺾이면 매도`,
    ];
  }
  return [];
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
