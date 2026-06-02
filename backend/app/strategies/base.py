"""전략 공통 인터페이스 및 신호 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Signal:
    symbol: str
    strategy: str
    side: Side
    price: float | None
    reason: str


class Strategy(Protocol):
    name: str

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        """종가 시계열을 평가해 신호를 반환한다. 신호 없으면 None."""
        ...
