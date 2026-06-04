"""RSI + 이동평균(MA) 추세 필터 전략 (틱봉 집계).

raw 틱은 노이즈가 커서, 원시 틱을 N개씩 묶은 '틱봉'의 종가 위에서 RSI·MA를 계산한다
(bar_ticks=50 → 50틱봉). bar_ticks=1이면 원시 틱과 동일.

매매 규칙(틱봉 종가 기준):
- 매수: 현재가 > MA(상승추세) **그리고** RSI가 과매도(low)를 아래→위로 회복.
- 매도(둘 중 하나): RSI가 과매수(high)를 위→아래로 이탈, **또는** 현재가가 MA를
        위→아래로 하향 돌파(추세 이탈 청산 = 안전장치). 추세선이 깨지는 그 순간만 1회.

단일 RSI의 약점(하락추세에서 과매도 신호 남발)을 MA 필터로 막고, 매수 근거(추세)가
깨지면(현재가 < MA) 즉시 빠져나와 하방을 제한한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.strategies.base import Signal
from app.strategies.indicators import closed_ticks, rolling_sma, rsi, to_tick_bars


@dataclass
class RsiMaStrategy:
    rsi_period: int = 14
    low: float = 30.0
    high: float = 70.0
    ma_period: int = 50
    bar_ticks: int = 50
    name: str = "rsi_ma"

    def __post_init__(self) -> None:
        if self.rsi_period < 2:
            raise ValueError("rsi_period는 2 이상이어야 합니다")
        if self.ma_period < 2:
            raise ValueError("ma_period는 2 이상이어야 합니다")
        if self.bar_ticks < 1:
            raise ValueError("bar_ticks는 1 이상이어야 합니다")
        if not (0 < self.low < self.high < 100):
            raise ValueError("0 < low < high < 100 이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        # 확정봉만 평가한다(진행 중 미완성 틱봉 제외 → 매 틱 재샘플링 휘프소 방지).
        bars = to_tick_bars(closed_ticks(closes, self.bar_ticks), self.bar_ticks)
        # RSI는 직전·현재 2개, MA는 직전·현재 2개(크로스 판정) 값이 필요하다.
        if len(bars) < max(self.rsi_period + 2, self.ma_period + 1):
            return None

        rsi_values = rsi(bars, self.rsi_period)
        ma_values = rolling_sma(bars, self.ma_period)  # Rolling SMA(러닝 합계)
        prev_rsi = rsi_values.iloc[-2]
        cur_rsi = rsi_values.iloc[-1]
        prev_ma = ma_values[-2]
        cur_ma = ma_values[-1]
        if pd.isna(prev_rsi) or pd.isna(cur_rsi) or prev_ma is None or cur_ma is None:
            return None

        prev_price = bars[-2]
        cur_price = bars[-1]
        order_price = closes[-1]  # 실제 주문가는 최신 틱

        # 매수: 현재가 > MA(상승추세) + RSI 과매도 상향 돌파
        if cur_price > cur_ma and prev_rsi < self.low <= cur_rsi:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=order_price,
                reason=f"상승추세(현재가>MA{self.ma_period}) RSI 과매도 회복 {prev_rsi:.1f}→{cur_rsi:.1f}",
            )

        # 매도: RSI 과매수 하향 이탈 OR 추세 이탈(현재가가 MA 하향 돌파)
        rsi_overbought_exit = prev_rsi > self.high >= cur_rsi
        ma_breakdown = prev_price >= prev_ma and cur_price < cur_ma
        if rsi_overbought_exit or ma_breakdown:
            reason = (
                f"RSI 과매수 이탈 {prev_rsi:.1f}→{cur_rsi:.1f}"
                if rsi_overbought_exit
                else f"추세 이탈(현재가<MA{self.ma_period})"
            )
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=order_price,
                reason=reason,
            )

        return None
