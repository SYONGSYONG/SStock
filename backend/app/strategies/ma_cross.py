"""이동평균 크로스 전략 (+ 실전 거버너 필터).

골든 크로스(단기선이 장기선을 상향 돌파) → 매수, 데드 크로스 → 매도. 이동평균은 Rolling
SMA로 계산하며 '틱봉'(bar_ticks개 묶음)의 종가 위에서 구한다. 진행 중 미완성 틱봉은
`closed_ticks`로 제외한다(확정봉만 평가).

실전 거버너 필터(기본값은 현행과 동일한 중립값):
- `confirm_bars`: 교차 후 N봉 유지돼야 신호(1 = 교차 즉시 = 현행).
- `diff_buffer_ticks`: 단기−장기 MA 차이가 `tick_size × N` 이상일 때만 인정(살짝 교차 무시).
- `trend_ma`: 상위 추세 MA(0=off). 매수는 현재가 > 이 MA일 때만, 현재가 < 이 MA면 매도.
- `use_long_slope`: 장기 MA가 우상향일 때만 매수.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.strategies.base import Signal
from app.strategies.indicators import closed_ticks, rolling_sma, to_tick_bars
from app.strategies.market_rules import tick_size


@dataclass
class MaCrossStrategy:
    short: int = 5
    long: int = 20
    bar_ticks: int = 50
    confirm_bars: int = 1
    diff_buffer_ticks: int = 0
    trend_ma: int = 0  # 0 = 사용 안 함
    use_long_slope: bool = False
    name: str = "ma_cross"

    def __post_init__(self) -> None:
        if self.short >= self.long:
            raise ValueError("short는 long보다 작아야 합니다")
        if self.bar_ticks < 1:
            raise ValueError("bar_ticks는 1 이상이어야 합니다")
        if self.confirm_bars < 1:
            raise ValueError("confirm_bars는 1 이상이어야 합니다")
        if self.diff_buffer_ticks < 0:
            raise ValueError("diff_buffer_ticks는 0 이상이어야 합니다")
        if self.trend_ma < 0:
            raise ValueError("trend_ma는 0 이상이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        bars = to_tick_bars(closed_ticks(closes, self.bar_ticks), self.bar_ticks)
        cb = self.confirm_bars
        need = max(self.long + cb, self.trend_ma)
        if len(bars) < need:
            return None

        short_ma = rolling_sma(bars, self.short)
        long_ma = rolling_sma(bars, self.long)
        price = closes[-1]
        buf = tick_size(price) * self.diff_buffer_ticks

        # 최근 cb봉 동안 단기>장기 유지 + 그 직전 봉엔 단기<=장기(= cb봉 전 골든크로스)
        held_up = all(short_ma[-k] > long_ma[-k] for k in range(1, cb + 1))
        crossed_up = short_ma[-(cb + 1)] <= long_ma[-(cb + 1)]
        held_down = all(short_ma[-k] < long_ma[-k] for k in range(1, cb + 1))
        crossed_down = short_ma[-(cb + 1)] >= long_ma[-(cb + 1)]
        cur_gap = short_ma[-1] - long_ma[-1]

        # 상위 추세 필터
        trend_ok_buy = True
        trend_break_sell = False
        if self.trend_ma:
            tm = rolling_sma(bars, self.trend_ma)[-1]
            if tm is not None:
                trend_ok_buy = price > tm
                trend_break_sell = price < tm
        slope_ok = (not self.use_long_slope) or (long_ma[-1] > long_ma[-2])

        # 매수: 골든크로스 confirm + 이격폭 + 추세 필터
        if held_up and crossed_up and cur_gap >= buf and trend_ok_buy and slope_ok:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=price,
                reason=f"골든크로스 MA{self.short}>MA{self.long}"
                + (f"·{cb}봉확인" if cb > 1 else ""),
            )

        # 매도: 데드크로스 confirm + 이격폭, 또는 추세 이탈(현재가<추세MA)
        if (held_down and crossed_down and -cur_gap >= buf) or trend_break_sell:
            reason = (
                f"추세이탈(현재가<MA{self.trend_ma})"
                if trend_break_sell and not (held_down and crossed_down)
                else f"데드크로스 MA{self.short}<MA{self.long}"
                + (f"·{cb}봉확인" if cb > 1 else "")
            )
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=price,
                reason=reason,
            )
        return None
