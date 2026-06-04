"""전략 설정(name + params)으로부터 전략 인스턴스를 생성한다."""

from __future__ import annotations

from typing import Any

from app.strategies.base import Strategy
from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.rsi_ma import RsiMaStrategy

STRATEGY_NAMES = ("ma_cross", "rsi_ma")


def build_strategy(name: str, params: dict[str, Any] | None = None) -> Strategy:
    params = params or {}
    if name == "ma_cross":
        return MaCrossStrategy(
            short=int(params.get("short", 5)),
            long=int(params.get("long", 20)),
            bar_ticks=int(params.get("bar_ticks", 50)),
            confirm_bars=int(params.get("confirm_bars", 1)),
            diff_buffer_ticks=int(params.get("diff_buffer_ticks", 0)),
            trend_ma=int(params.get("trend_ma", 0)),
            use_long_slope=bool(params.get("use_long_slope", 0)),
        )
    if name == "rsi_ma":
        return RsiMaStrategy(
            rsi_period=int(params.get("rsi_period", 14)),
            low=float(params.get("low", 30.0)),
            high=float(params.get("high", 70.0)),
            ma_period=int(params.get("ma_period", 50)),
            bar_ticks=int(params.get("bar_ticks", 50)),
            confirm_bars=int(params.get("confirm_bars", 1)),
            ma_buffer_ticks=int(params.get("ma_buffer_ticks", 0)),
            max_distance_ticks=int(params.get("max_distance_ticks", 0)),
        )
    raise ValueError(f"알 수 없는 전략: {name}")
