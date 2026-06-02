"""이동평균 크로스 전략.

골든 크로스(단기선이 장기선을 상향 돌파) → 매수.
데드 크로스(단기선이 장기선을 하향 돌파) → 매도.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.strategies.base import Signal
from app.strategies.indicators import sma


@dataclass
class MaCrossStrategy:
    short: int = 5
    long: int = 20
    name: str = "ma_cross"

    def __post_init__(self) -> None:
        if self.short >= self.long:
            raise ValueError("short는 long보다 작아야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        if len(closes) < self.long + 1:
            return None
        short_ma = sma(closes, self.short)
        long_ma = sma(closes, self.long)
        prev_diff = short_ma.iloc[-2] - long_ma.iloc[-2]
        cur_diff = short_ma.iloc[-1] - long_ma.iloc[-1]
        price = closes[-1]

        if prev_diff <= 0 < cur_diff:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=price,
                reason=f"골든크로스 MA{self.short}>MA{self.long}",
            )
        if prev_diff >= 0 > cur_diff:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=price,
                reason=f"데드크로스 MA{self.short}<MA{self.long}",
            )
        return None
