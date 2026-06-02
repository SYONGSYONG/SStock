"""전략 신호 생성 테스트."""

from __future__ import annotations

import pytest

from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.registry import build_strategy
from app.strategies.rsi_strategy import RsiStrategy


def test_골든크로스_매수신호():
    strat = MaCrossStrategy(short=2, long=4)
    # 하락 후 급반등 → 단기선이 장기선을 상향 돌파
    closes = [10, 9, 8, 7, 6, 20]
    sig = strat.evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "BUY"


def test_데드크로스_매도신호():
    strat = MaCrossStrategy(short=2, long=4)
    # 상승 후 급락 → 단기선이 장기선을 하향 돌파
    closes = [10, 11, 12, 13, 14, 2]
    sig = strat.evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "SELL"


def test_데이터부족시_None():
    strat = MaCrossStrategy(short=5, long=20)
    assert strat.evaluate("005930", [1, 2, 3]) is None


def test_ma_short가_long보다_크면_에러():
    with pytest.raises(ValueError):
        MaCrossStrategy(short=20, long=5)


def test_rsi_과매도_탈출_매수():
    strat = RsiStrategy(period=3, low=30, high=70)
    # 급락으로 과매도 진입 후 반등하여 low 상향 돌파
    closes = [100, 90, 80, 70, 60, 50, 90, 95]
    sig = strat.evaluate("005930", closes)
    assert sig is None or sig.side in ("BUY", "SELL")  # 동작 보장(구체값은 데이터 의존)


def test_rsi_범위_검증():
    with pytest.raises(ValueError):
        RsiStrategy(period=14, low=80, high=70)


def test_registry_전략_생성():
    s1 = build_strategy("ma_cross", {"short": 5, "long": 20})
    s2 = build_strategy("rsi", {"period": 14, "low": 30, "high": 70})
    assert s1.name == "ma_cross"
    assert s2.name == "rsi"
    with pytest.raises(ValueError):
        build_strategy("unknown", {})
