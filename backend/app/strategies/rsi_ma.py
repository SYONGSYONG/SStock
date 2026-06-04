"""RSI + 이동평균(MA) 추세 필터 전략 (틱봉 집계 + 실전 거버너 필터).

매수: 현재가 > MA(상승추세) + RSI가 과매도(low)를 아래→위 회복.
매도: RSI가 과매수(high)를 위→아래 이탈, 또는 현재가가 MA를 하향 돌파(추세 이탈 청산).

실전 거버너 필터(기본값은 현행과 동일한 중립값):
- `ma_buffer_ticks`: MA 위/아래 판정 히스테리시스. 상승추세=현재가>MA+버퍼, 이탈=현재가<MA−버퍼.
- `max_distance_ticks`: 현재가가 MA보다 `tick_size × N` 넘게 높으면 늦은 추격으로 보고 매수 보류(0=off).
- `confirm_bars`: RSI 회복/추세 이탈이 N봉 유지돼야 신호(1 = 현행).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.strategies.base import Signal
from app.strategies.indicators import closed_ticks, rolling_sma, rsi, to_tick_bars
from app.strategies.market_rules import tick_size


@dataclass
class RsiMaStrategy:
    rsi_period: int = 14
    low: float = 30.0
    high: float = 70.0
    ma_period: int = 50
    bar_ticks: int = 50
    confirm_bars: int = 1
    ma_buffer_ticks: int = 0
    max_distance_ticks: int = 0  # 0 = off
    name: str = "rsi_ma"

    def __post_init__(self) -> None:
        if self.rsi_period < 2:
            raise ValueError("rsi_period는 2 이상이어야 합니다")
        if self.ma_period < 2:
            raise ValueError("ma_period는 2 이상이어야 합니다")
        if self.bar_ticks < 1:
            raise ValueError("bar_ticks는 1 이상이어야 합니다")
        if self.confirm_bars < 1:
            raise ValueError("confirm_bars는 1 이상이어야 합니다")
        if self.ma_buffer_ticks < 0 or self.max_distance_ticks < 0:
            raise ValueError("버퍼/거리 틱은 0 이상이어야 합니다")
        if not (0 < self.low < self.high < 100):
            raise ValueError("0 < low < high < 100 이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        bars = to_tick_bars(closed_ticks(closes, self.bar_ticks), self.bar_ticks)
        cb = self.confirm_bars
        need = max(self.rsi_period + cb + 1, self.ma_period + cb + 1)
        if len(bars) < need:
            return None

        rsi_values = rsi(bars, self.rsi_period)
        ma_values = rolling_sma(bars, self.ma_period)
        order_price = closes[-1]  # 주문가는 최신 틱
        price = tick_size(order_price)
        buf = price * self.ma_buffer_ticks
        max_dist = price * self.max_distance_ticks

        def ma_at(i: int) -> float | None:
            return ma_values[i]

        def rsi_at(i: int) -> float | None:
            v = rsi_values.iloc[i]
            return None if pd.isna(v) else float(v)

        cur_ma = ma_at(-1)
        cur_price = bars[-1]
        if cur_ma is None:
            return None

        # 매수: 상승추세(현재가>MA+버퍼) + RSI 과매도 회복이 cb봉 유지 + 추격 거리 제한
        recovered = all((rsi_at(-k) is not None and rsi_at(-k) >= self.low) for k in range(1, cb + 1))
        before = rsi_at(-(cb + 1))
        crossed_up = before is not None and before < self.low
        uptrend = cur_price > cur_ma + buf
        not_too_far = self.max_distance_ticks == 0 or (cur_price - cur_ma) <= max_dist
        if uptrend and recovered and crossed_up and not_too_far:
            pr = rsi_at(-(cb + 1))
            cr = rsi_at(-1)
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=order_price,
                reason=f"상승추세(현재가>MA{self.ma_period}+{self.ma_buffer_ticks}틱) "
                f"RSI 과매도 회복 {pr:.1f}→{cr:.1f}",
            )

        # 매도①: RSI 과매수 하향 이탈(직전→현재)
        prev_rsi = rsi_at(-2)
        cur_rsi = rsi_at(-1)
        rsi_exit = (
            prev_rsi is not None
            and cur_rsi is not None
            and prev_rsi > self.high >= cur_rsi
        )
        # 매도②: 현재가가 MA−버퍼 아래로 cb봉 연속, 그 직전엔 위(추세 이탈 확인)
        below = True
        for k in range(1, cb + 1):
            m = ma_at(-k)
            if m is None or not (bars[-k] < m - buf):
                below = False
                break
        m_before = ma_at(-(cb + 1))
        broke_down = below and m_before is not None and bars[-(cb + 1)] >= m_before - buf

        if rsi_exit or broke_down:
            reason = (
                f"RSI 과매수 이탈 {prev_rsi:.1f}→{cur_rsi:.1f}"
                if rsi_exit
                else f"추세 이탈(현재가<MA{self.ma_period}−{self.ma_buffer_ticks}틱)"
            )
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=order_price,
                reason=reason,
            )
        return None
