"""이동평균 크로스 전략.

골든 크로스(단기선이 장기선을 상향 돌파) → 매수.
데드 크로스(단기선이 장기선을 하향 돌파) → 매도.

이동평균은 Rolling SMA(러닝 합계로 갱신하는 단순이동평균)로 계산한다 — 매 지점마다
최근 N개를 다시 더하지 않고 한 번의 순회로 구한다. 산출값은 일반 SMA와 동일하다.

원시 틱은 노이즈가 커서 bar_ticks개씩 묶은 '틱봉'의 종가 위에서 MA를 계산한다
(bar_ticks=50 → 50틱봉). bar_ticks=1이면 원시 틱과 동일.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.strategies.base import Signal
from app.strategies.indicators import closed_ticks, rolling_sma, to_tick_bars


@dataclass
class MaCrossStrategy:
    short: int = 5
    long: int = 20
    bar_ticks: int = 50
    name: str = "ma_cross"

    def __post_init__(self) -> None:
        if self.short >= self.long:
            raise ValueError("short는 long보다 작아야 합니다")
        if self.bar_ticks < 1:
            raise ValueError("bar_ticks는 1 이상이어야 합니다")

    def evaluate(self, symbol: str, closes: list[float]) -> Signal | None:
        # 확정봉만 평가한다(진행 중 미완성 틱봉 제외 → 매 틱 재샘플링 휘프소 방지).
        bars = to_tick_bars(closed_ticks(closes, self.bar_ticks), self.bar_ticks)
        if len(bars) < self.long + 1:
            return None
        short_ma = rolling_sma(bars, self.short)
        long_ma = rolling_sma(bars, self.long)
        # len(bars) >= long+1 이므로 마지막 두 지점의 단기·장기 SMA는 모두 유효(None 아님).
        prev_diff = short_ma[-2] - long_ma[-2]
        cur_diff = short_ma[-1] - long_ma[-1]
        price = closes[-1]  # 주문가는 최신 틱(신호 판정은 확정봉, 체결가는 현재가)

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
