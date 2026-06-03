"""RSI + 이동평균(MA) 추세 필터 전략.

추세 필터(MA)로 매수 방향을 거른 뒤 RSI로 진입 타이밍을 잡는다.
- 매수: 현재가가 추세선(MA) 위에 있는 상승추세에서만, RSI가 과매도(low)를 상향 돌파할 때.
        → 상승 흐름 속 일시적 눌림목만 매수(하락추세 역행 매수 차단).
- 매도: RSI가 과매수(high)를 하향 이탈할 때(추세 무관, 과열 시 청산).

단일 RSI의 약점(강한 하락추세에서 과매도 신호 남발 → 떨어지는 칼날 매수)을 MA 필터로 막는다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.strategies.base import Signal
from app.strategies.indicators import rsi, sma


@dataclass
class RsiMaStrategy:
    rsi_period: int = 14
    low: float = 30.0
    high: float = 70.0
    ma_period: int = 50
    name: str = "rsi_ma"

    def __post_init__(self) -> None:
        if self.rsi_period < 2:
            raise ValueError("rsi_period는 2 이상이어야 합니다")
        if self.ma_period < 2:
            raise ValueError("ma_period는 2 이상이어야 합니다")
        if not (0 < self.low < self.high < 100):
            raise ValueError("0 < low < high < 100 이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        # RSI는 직전·현재 2개 값이, MA는 현재 값이 필요하다.
        if len(closes) < max(self.rsi_period + 2, self.ma_period + 1):
            return None

        rsi_values = rsi(closes, self.rsi_period)
        ma_values = sma(closes, self.ma_period)
        prev = rsi_values.iloc[-2]
        cur = rsi_values.iloc[-1]
        ma_now = ma_values.iloc[-1]
        if pd.isna(prev) or pd.isna(cur) or pd.isna(ma_now):
            return None

        price = closes[-1]

        # 매수: 상승추세(현재가 > MA) + RSI 과매도 상향 돌파
        if price > ma_now and prev <= self.low < cur:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="BUY",
                price=price,
                reason=(
                    f"상승추세(>MA{self.ma_period}) RSI 과매도 탈출 {prev:.1f}→{cur:.1f}"
                ),
            )

        # 매도: RSI 과매수 하향 이탈(추세 무관 청산)
        if prev >= self.high > cur:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                side="SELL",
                price=price,
                reason=f"RSI 과매수 이탈 {prev:.1f}→{cur:.1f}",
            )

        return None
