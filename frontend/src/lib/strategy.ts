// 전략 식별자 → 사람이 읽는 라벨 (전략 패널 / 매매 신호 공통)
export const STRATEGY_LABEL: Record<string, string> = {
  ma_cross: "이동평균 크로스",
  rsi_ma: "RSI + MA 필터",
};

/** 전략별 기본 파라미터 값(단일 진실 공급원).
 *  거버너 파라미터는 **실전 추천값**을 기본으로 채운다(엔진은 값이 없으면 중립으로 동작). */
export const STRATEGY_DEFAULTS: Record<string, Record<string, number>> = {
  ma_cross: {
    short: 10,
    long: 40,
    bar_ticks: 50,
    confirm_bars: 2,
    diff_buffer_ticks: 2,
    trend_ma: 100,
    use_long_slope: 1,
    min_hold_bars: 8,
    cooldown_bars: 15,
    stop_loss_ticks: 5,
    trailing_stop_ticks: 5,
    take_profit_ticks: 0,
    min_volatility_ticks: 0,
    min_turnover: 0,
    max_spread_ticks: 0,
  },
  rsi_ma: {
    rsi_period: 21,
    low: 30,
    high: 75,
    ma_period: 80,
    bar_ticks: 50,
    confirm_bars: 2,
    ma_buffer_ticks: 2,
    max_distance_ticks: 8,
    min_hold_bars: 8,
    cooldown_bars: 15,
    stop_loss_ticks: 5,
    trailing_stop_ticks: 5,
    take_profit_ticks: 0,
    min_volatility_ticks: 0,
    min_turnover: 0,
    max_spread_ticks: 0,
  },
};

/** ma_cross 상황별 프리셋(추천 파라미터 묶음).
 *  전략 추가 폼에서 이동평균 크로스를 고른 뒤 프리셋을 선택하면 파라미터를 한 번에 채운다.
 *  내부 전략은 ma_cross 그대로이며, 프리셋은 파라미터 템플릿일 뿐이다. */
export interface MaCrossPreset {
  key: string;
  label: string;
  purpose: string;
  params: Record<string, number>;
}

export const MA_CROSS_PRESETS: MaCrossPreset[] = [
  {
    key: "강한상승",
    label: "강한상승",
    purpose: "안정적인 상승 추세 진입",
    params: {
      short: 10,
      long: 40,
      bar_ticks: 50,
      confirm_bars: 2,
      diff_buffer_ticks: 2,
      trend_ma: 100,
      use_long_slope: 1,
      min_hold_bars: 8,
      cooldown_bars: 15,
      stop_loss_ticks: 12,
      trailing_stop_ticks: 15,
      take_profit_ticks: 0,
      min_volatility_ticks: 10,
      min_turnover: 0,
      max_spread_ticks: 3,
    },
  },
  {
    key: "아주강한상승",
    label: "아주강한상승",
    purpose: "장초반 급등·폭등 대응",
    params: {
      short: 5,
      long: 20,
      bar_ticks: 30,
      confirm_bars: 2,
      diff_buffer_ticks: 2,
      trend_ma: 0,
      use_long_slope: 1,
      min_hold_bars: 5,
      cooldown_bars: 8,
      stop_loss_ticks: 15,
      trailing_stop_ticks: 20,
      take_profit_ticks: 0,
      min_volatility_ticks: 15,
      min_turnover: 0,
      max_spread_ticks: 5,
    },
  },
  {
    key: "강한하강",
    label: "강한하강",
    purpose: "보유 종목 방어·매수 억제",
    params: {
      short: 8,
      long: 32,
      bar_ticks: 30,
      confirm_bars: 2,
      diff_buffer_ticks: 2,
      trend_ma: 60,
      use_long_slope: 1,
      min_hold_bars: 0,
      cooldown_bars: 20,
      stop_loss_ticks: 6,
      trailing_stop_ticks: 8,
      take_profit_ticks: 0,
      min_volatility_ticks: 0,
      min_turnover: 0,
      max_spread_ticks: 3,
    },
  },
  {
    key: "아주강한하강",
    label: "아주강한하강",
    purpose: "급락 대응·빠른 청산 우선",
    params: {
      short: 3,
      long: 10,
      bar_ticks: 15,
      confirm_bars: 1,
      diff_buffer_ticks: 1,
      trend_ma: 40,
      use_long_slope: 1,
      min_hold_bars: 0,
      cooldown_bars: 30,
      stop_loss_ticks: 3,
      trailing_stop_ticks: 5,
      take_profit_ticks: 0,
      min_volatility_ticks: 0,
      min_turnover: 0,
      max_spread_ticks: 3,
    },
  },
];

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
    { key: "bar_ticks", label: "틱봉", min: 1, max: 2000 },
    { key: "confirm_bars", label: "확인봉", min: 1, max: 20 },
    { key: "diff_buffer_ticks", label: "이격틱", min: 0, max: 50 },
    { key: "trend_ma", label: "추세MA(0=off)", min: 0, max: 999 },
    { key: "use_long_slope", label: "우상향필터(0/1)", min: 0, max: 1 },
    { key: "min_hold_bars", label: "최소보유봉", min: 0, max: 100 },
    { key: "cooldown_bars", label: "쿨다운봉", min: 0, max: 100 },
    { key: "stop_loss_ticks", label: "손절틱(0=off)", min: 0, max: 200 },
    { key: "trailing_stop_ticks", label: "트레일링틱(0=off)", min: 0, max: 200 },
    { key: "take_profit_ticks", label: "익절틱(0=off)", min: 0, max: 500 },
    { key: "min_volatility_ticks", label: "최소변동틱(0=off)", min: 0, max: 1000 },
    { key: "min_turnover", label: "최소거래대금(0=off)", min: 0, max: 1_000_000_000 },
    { key: "max_spread_ticks", label: "최대스프레드틱(0=off)", min: 0, max: 50 },
  ],
  rsi_ma: [
    { key: "rsi_period", label: "RSI 기간", min: 2, max: 999 },
    { key: "low", label: "과매도", min: 1, max: 99 },
    { key: "high", label: "과매수", min: 1, max: 99 },
    { key: "ma_period", label: "추세 MA", min: 2, max: 999 },
    { key: "bar_ticks", label: "틱봉", min: 1, max: 2000 },
    { key: "confirm_bars", label: "확인봉", min: 1, max: 20 },
    { key: "ma_buffer_ticks", label: "MA버퍼틱", min: 0, max: 50 },
    { key: "max_distance_ticks", label: "추격거리틱(0=off)", min: 0, max: 200 },
    { key: "min_hold_bars", label: "최소보유봉", min: 0, max: 100 },
    { key: "cooldown_bars", label: "쿨다운봉", min: 0, max: 100 },
    { key: "stop_loss_ticks", label: "손절틱(0=off)", min: 0, max: 200 },
    { key: "trailing_stop_ticks", label: "트레일링틱(0=off)", min: 0, max: 200 },
    { key: "take_profit_ticks", label: "익절틱(0=off)", min: 0, max: 500 },
    { key: "min_volatility_ticks", label: "최소변동틱(0=off)", min: 0, max: 1000 },
    { key: "min_turnover", label: "최소거래대금(0=off)", min: 0, max: 1_000_000_000 },
    { key: "max_spread_ticks", label: "최대스프레드틱(0=off)", min: 0, max: 50 },
  ],
};

/** 파라미터 유효성 검사. 통과하면 null, 위반하면 한국어 오류 메시지. */
export function validateParams(
  strategy: string,
  params: Record<string, number>,
): string | null {
  if (strategy === "ma_cross") {
    if (![params.short, params.long, params.bar_ticks].every(Number.isFinite)) {
      return "단기·장기·틱봉 값을 입력하세요";
    }
    if (params.short < 1 || params.long < 2) {
      return "단기는 1 이상, 장기는 2 이상이어야 합니다";
    }
    if (params.short >= params.long) {
      return "단기는 장기보다 작아야 합니다";
    }
    if (params.bar_ticks < 1) {
      return "틱봉은 1 이상이어야 합니다";
    }
  }
  if (strategy === "rsi_ma") {
    const { rsi_period, low, high, ma_period, bar_ticks } = params;
    if (![rsi_period, low, high, ma_period, bar_ticks].every(Number.isFinite)) {
      return "RSI 기간·과매도·과매수·추세 MA·틱봉 값을 입력하세요";
    }
    if (rsi_period < 2) {
      return "RSI 기간은 2 이상이어야 합니다";
    }
    if (ma_period < 2) {
      return "추세 MA는 2 이상이어야 합니다";
    }
    if (bar_ticks < 1) {
      return "틱봉은 1 이상이어야 합니다";
    }
    if (!(low > 0 && low < high && high < 100)) {
      return "0 < 과매도 < 과매수 < 100 이어야 합니다";
    }
  }
  // 거버너 등 정의된 모든 필드는 (입력된 경우) 범위 안이어야 한다.
  for (const f of STRATEGY_PARAM_FIELDS[strategy] ?? []) {
    const v = params[f.key];
    if (v === undefined) continue;
    if (!Number.isFinite(v) || v < f.min || v > f.max) {
      return `${f.label}는 ${f.min}~${f.max} 범위여야 합니다`;
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
  /** 상황을 곁들인 예시(이해를 돕는 시나리오). */
  examples: string[];
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
    examples: [
      "상황①(매수): 50틱봉에서 주가가 6,000원까지 밀렸다가 반등해 MA10이 MA40을 아래→위로 뚫고 2봉(확인봉) 유지 → 골든크로스 매수. 단, 이격이 2틱 미만으로 살짝만 스치면 무시합니다.",
      "상황②(매도): 보유 중 주가가 꺾여 MA10이 MA40 아래로 내려가 2봉 유지 → 데드크로스 매도. 추세MA(예: MA100) 아래로 떨어지면 더 빨리 청산합니다.",
      "상황③(휘프소 방지): 횡보장에서 두 선이 계속 붙었다 떨어졌다 하면, 확인봉·이격폭 필터가 잔신호를 걸러 잦은 왕복매매를 줄입니다.",
    ],
    note: "이동평균은 Rolling SMA(러닝 합계)로 가볍게 계산하며, 원시 틱이 아니라 ‘틱봉’ 단위로 평균을 냅니다(틱봉 50 → 50틱봉). 틱봉이 클수록 노이즈가 줄지만 워밍업이 길어집니다 — 50틱봉×장기40이면 첫 신호까지 약 2,050틱 필요, 봇 재시작 시 다시 누적합니다.",
  },
  rsi_ma: {
    title: "RSI + MA 필터",
    summary:
      "추세 필터(MA)로 매수 방향을 거른 뒤 RSI로 진입 타이밍을 잡고, 추세가 깨지면 즉시 빠져나오는 전략입니다. ‘상승추세일 때만 눌린 자리에서 사고, 과열되거나 추세가 무너지면 판다’가 핵심입니다. 노이즈를 줄이려고 원시 틱을 ‘틱봉’으로 묶어 그 종가 위에서 RSI·MA를 계산합니다(틱봉 50 → 50틱봉).",
    rules: [
      "매수: 현재가가 추세선(MA) 위(상승추세) + RSI가 과매도선(low)을 아래→위로 회복",
      "매도①: RSI가 과매수선(high)을 위→아래로 이탈(과열 청산)",
      "매도②(안전장치): 현재가가 MA를 위→아래로 하향 돌파(추세 이탈 — 그 순간 1회)",
      "하락추세(현재가 < MA)에서는 RSI 과매도여도 매수하지 않음(필터 차단)",
    ],
    examples: [
      "상황①(매수): 주가가 추세MA(50틱봉 MA80) 위에 있는 상승추세에서, 잠깐 눌리며 RSI가 30 아래로 갔다가 30 위로 회복 → 눌림목 매수. 단, 현재가가 MA보다 너무 높이(추격거리 초과) 떠 있으면 늦은 추격으로 보고 보류합니다.",
      "상황②(매도): 보유 중 RSI가 75 위로 과열됐다가 75 아래로 꺾이면 → 과열 청산. 또는 현재가가 MA−2틱 아래로 2봉 유지되면 추세 이탈로 청산합니다.",
      "상황③(노이즈 보류): 현재가가 MA 바로 위아래 ±2틱 안에서 오락가락하면 → 추세 판단을 보류해 잦은 진입을 막습니다.",
    ],
    note: "‘틱봉’ 단위로 계산합니다. 틱봉이 클수록(50~100) 노이즈가 줄어 안정적이지만, 워밍업이 길어집니다 — 예: 50틱봉×MA80이면 첫 신호까지 약 4,050틱이 필요하고 봇 재시작 시 다시 누적합니다. 추세 MA는 느릴수록 필터가 잘 동작합니다(너무 짧으면 눌림에 현재가가 MA 아래로 내려가 매수가 막힘).",
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
    const bt = params.bar_ticks ?? "-";
    return [
      `틱봉 ${bt} = 원시 틱 ${bt}개를 한 봉으로 묶어 그 종가로 계산(클수록 노이즈↓)`,
      `단기 ${short} = 틱봉 ${short}개의 평균선(MA${short}) — 빠르게 반응`,
      `장기 ${long} = 틱봉 ${long}개의 평균선(MA${long}) — 느리게 반응(추세)`,
      `MA${short}가 MA${long}을 위로 뚫으면 매수, 아래로 뚫으면 매도`,
    ];
  }
  if (strategy === "rsi_ma") {
    const rp = params.rsi_period ?? "-";
    const low = params.low ?? "-";
    const high = params.high ?? "-";
    const mp = params.ma_period ?? "-";
    const bt = params.bar_ticks ?? "-";
    return [
      `틱봉 ${bt} = 원시 틱 ${bt}개를 한 봉으로 묶어 그 종가로 계산(클수록 노이즈↓)`,
      `RSI 기간 ${rp} = 틱봉 ${rp}개로 강도 계산`,
      `추세 MA ${mp} = 틱봉 ${mp}개 평균선(MA${mp}). 현재가가 이 위면 상승추세로 보고 매수 허용`,
      `과매도 ${low} = 상승추세에서 RSI가 이 값을 상향 돌파하면 매수`,
      `과매수 ${high} = RSI가 이 값을 하향 이탈하면 매도(추세 이탈해도 매도)`,
    ];
  }
  return [];
}

/** 전략 + 파라미터를 한 줄 설명으로 변환한다. */
export function describeStrategy(strategy: string, params: Record<string, number>): string {
  if (strategy === "ma_cross") {
    return `이동평균 크로스 · ${params.bar_ticks ?? "-"}틱봉 · 단기 ${params.short ?? "-"} / 장기 ${params.long ?? "-"}`;
  }
  if (strategy === "rsi_ma") {
    return `RSI + MA · ${params.bar_ticks ?? "-"}틱봉 · RSI ${params.rsi_period ?? "-"} · 과매도 ${params.low ?? "-"} / 과매수 ${params.high ?? "-"} · MA ${params.ma_period ?? "-"}`;
  }
  return strategyLabel(strategy);
}

/** 전략 비교표 한 행(구분 + 두 전략 설명). */
export interface StrategyCompareRow {
  label: string;
  ma_cross: string;
  rsi_ma: string;
}

/** 이동평균 크로스 vs RSI + MA 필터 비교(도움말 옆 '전략 비교' 팝업). */
export const STRATEGY_COMPARISON: StrategyCompareRow[] = [
  { label: "전략 성격", ma_cross: "추세 전환 / 추세 추종", rsi_ma: "추세 필터 + 눌림목 반등" },
  {
    label: "핵심 질문",
    ma_cross: "“방금 추세가 위로 바뀌었나?”",
    rsi_ma: "“상승 추세 중 잠깐 눌렸다가 회복하나?”",
  },
  {
    label: "매수 신호",
    ma_cross: "단기 MA가 장기 MA 상향 돌파",
    rsi_ma: "MA 위에서 RSI가 과매도 회복",
  },
  {
    label: "매도 신호",
    ma_cross: "단기 MA가 장기 MA 하향 이탈",
    rsi_ma: "RSI 과매수 이탈 또는 MA 이탈",
  },
  { label: "장점", ma_cross: "강한 추세 초입을 잡기 좋음", rsi_ma: "추격매수 줄이고 눌림목 진입에 좋음" },
  { label: "단점", ma_cross: "횡보장에서 가짜 신호 많음", rsi_ma: "강한 급등 초입은 놓칠 수 있음" },
  { label: "잘 맞는 장", ma_cross: "강한 상승장, 추세장", rsi_ma: "상승장 눌림목, 완만한 우상향" },
  { label: "약한 장", ma_cross: "횡보장", rsi_ma: "급등장, 강한 하락장" },
];
