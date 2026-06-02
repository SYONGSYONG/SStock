"""RSI 전략.

과매도 구간(low)을 상향 돌파 → 매수.
과매수 구간(high)을 하향 돌파 → 매도.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.strategies.base import Signal
from app.strategies.indicators import rsi


@dataclass
class RsiStrategy:
    period: int = 14
    low: float = 30.0
    high: float = 70.0
    name: str = "rsi"

    def __post_init__(self) -> None:
        if not (0 < self.low < self.high < 100):
            raise ValueError("0 < low < high < 100 이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        if len(closes) < self.period + 2:
            return None
        values = rsi(closes, self.period)
        prev = values.iloc[-2]
        cur = values.iloc[-1]
        if pd.isna(prev) or pd.isna(cur):
            return None
        price = closes[-1]

        if prev <= self.low < cur:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=price,
                reason=f"RSI 과매도 탈출 {prev:.1f}→{cur:.1f}",
            )
        if prev >= self.high > cur:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=price,
                reason=f"RSI 과매수 이탈 {prev:.1f}→{cur:.1f}",
            )
        return None
