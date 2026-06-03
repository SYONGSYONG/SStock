"""전략 신호 생성 테스트."""

from __future__ import annotations

import pytest

from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.registry import build_strategy


def test_골든크로스_매수신호():
    # bar_ticks=1(원시 틱)로 소량 데이터에서 크로스 로직만 검증
    strat = MaCrossStrategy(short=2, long=4, bar_ticks=1)
    # 하락 후 급반등 → 단기선이 장기선을 상향 돌파
    closes = [10, 9, 8, 7, 6, 20]
    sig = strat.evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "BUY"


def test_데드크로스_매도신호():
    strat = MaCrossStrategy(short=2, long=4, bar_ticks=1)
    # 상승 후 급락 → 단기선이 장기선을 하향 돌파
    closes = [10, 11, 12, 13, 14, 2]
    sig = strat.evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "SELL"


def test_틱봉_집계_크로스():
    """각 봉 종가를 bar_ticks번 반복한 원시 틱 → 집계하면 봉열이 복원되어 동일 신호."""
    bars = [10, 9, 8, 7, 6, 20]
    raw: list[float] = []
    for b in bars:
        raw.extend([float(b)] * 4)
    sig = MaCrossStrategy(short=2, long=4, bar_ticks=4).evaluate("005930", raw)
    assert sig is not None
    assert sig.side == "BUY"


def test_데이터부족시_None():
    strat = MaCrossStrategy(short=5, long=20, bar_ticks=1)
    assert strat.evaluate("005930", [1, 2, 3]) is None


def test_ma_short가_long보다_크면_에러():
    with pytest.raises(ValueError):
        MaCrossStrategy(short=20, long=5)


def test_bar_ticks_검증():
    with pytest.raises(ValueError):
        MaCrossStrategy(short=5, long=20, bar_ticks=0)


def test_registry_전략_생성():
    s1 = build_strategy("ma_cross", {"short": 5, "long": 20, "bar_ticks": 50})
    assert s1.name == "ma_cross"
    assert s1.bar_ticks == 50
    with pytest.raises(ValueError):
        build_strategy("rsi", {})  # 기본 RSI는 제거됨 → 알 수 없는 전략
    with pytest.raises(ValueError):
        build_strategy("unknown", {})
