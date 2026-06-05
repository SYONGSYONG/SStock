"""시장 국면(regime) 분류 — 오토모드 1단계(그림자) 추천용.

종목 종가 히스토리로 현재 장세를 5국면 중 하나로 판별한다(프리셋 키와 동일).
1단계에서는 **판별·기록만** 하며 실제 프리셋 전환·주문에는 관여하지 않는다.
순수 함수로 구현해 테스트로 고정한다(상세: docs/11-strategy.md '오토모드 1단계').
"""

from __future__ import annotations

from app.strategies.indicators import closed_ticks, rolling_sma, to_tick_bars
from app.strategies.market_rules import tick_size

# 5개 국면 = 프리셋 키와 동일
REGIME_STRONG_UP = "강한상승"
REGIME_VERY_STRONG_UP = "아주강한상승"
REGIME_RANGE = "횡보노이즈"
REGIME_STRONG_DOWN = "강한하강"
REGIME_VERY_STRONG_DOWN = "아주강한하강"

# 로그·표시용 라벨(횡보노이즈만 슬래시 표기)
REGIME_LABEL: dict[str, str] = {
    REGIME_STRONG_UP: "강한상승",
    REGIME_VERY_STRONG_UP: "아주강한상승",
    REGIME_RANGE: "횡보/노이즈",
    REGIME_STRONG_DOWN: "강한하강",
    REGIME_VERY_STRONG_DOWN: "아주강한하강",
}

_REGIME_DEFAULTS: dict[str, float] = {
    "regime_bar_ticks": 50,       # 국면 판별용 틱봉 크기(안정 운용값)
    "regime_ma": 40,              # 추세 MA 기간(봉)
    "regime_slope_lookback": 5,   # 기울기 측정 봉 간격
    "regime_slope_ticks": 3,      # 추세로 인정할 기울기(틱)
    "regime_vol_lookback": 20,    # 변동성 측정 봉 수
    "regime_strong_vol_ticks": 30,  # '아주강한'으로 볼 변동성(틱)
}


def classify_regime(
    closes: list[float], params: dict[str, float] | None = None
) -> str | None:
    """종가 히스토리로 현재 시장 국면을 분류한다. 데이터 부족이면 None.

    틱봉 종가의 추세 MA 기울기(상승/하강/횡보)와 변동성(강한/아주강한)을 본다.
    반환값은 5개 국면 키 중 하나(프리셋 키와 동일).
    """
    cfg = {**_REGIME_DEFAULTS, **(params or {})}
    bar_ticks = int(cfg["regime_bar_ticks"]) or 1
    bars = to_tick_bars(closed_ticks(closes, bar_ticks), bar_ticks)

    ma_n = int(cfg["regime_ma"])
    slope_lb = int(cfg["regime_slope_lookback"])
    if ma_n < 1 or slope_lb < 1:
        return None
    if len(bars) < ma_n + slope_lb + 1:
        return None  # 확정봉 부족 → 미분류

    ma = rolling_sma(bars, ma_n)
    cur_ma = ma[-1]
    prev_ma = ma[-1 - slope_lb]
    if cur_ma is None or prev_ma is None:
        return None

    ts = tick_size(bars[-1])
    slope_ticks = (cur_ma - prev_ma) / ts

    vol_lb = int(cfg["regime_vol_lookback"])
    window = bars[-vol_lb:] if vol_lb > 0 else bars
    range_ticks = (max(window) - min(window)) / ts

    slope_thr = float(cfg["regime_slope_ticks"])
    strong_vol = float(cfg["regime_strong_vol_ticks"])

    if slope_ticks >= slope_thr:
        return REGIME_VERY_STRONG_UP if range_ticks >= strong_vol else REGIME_STRONG_UP
    if slope_ticks <= -slope_thr:
        return REGIME_VERY_STRONG_DOWN if range_ticks >= strong_vol else REGIME_STRONG_DOWN
    return REGIME_RANGE


def regime_label(regime: str | None) -> str:
    """국면 키 → 표시용 라벨(미분류면 빈 문자열)."""
    if regime is None:
        return ""
    return REGIME_LABEL.get(regime, regime)
