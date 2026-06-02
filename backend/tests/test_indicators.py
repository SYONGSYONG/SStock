"""지표 계산 테스트."""

from __future__ import annotations

import math

from app.strategies.indicators import rsi, sma


def test_단순이동평균():
    s = sma([1, 2, 3, 4, 5], period=3)
    assert math.isnan(s.iloc[0])
    assert math.isnan(s.iloc[1])
    assert s.iloc[2] == 2.0  # (1+2+3)/3
    assert s.iloc[3] == 3.0
    assert s.iloc[4] == 4.0


def test_rsi_지속상승은_100에_근접():
    closes = list(range(1, 30))  # 단조 증가 → 손실 0 → RSI 100
    r = rsi(closes, period=14)
    assert r.iloc[-1] == 100.0


def test_rsi_범위():
    closes = [10, 11, 10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18]
    r = rsi(closes, period=14)
    last = r.iloc[-1]
    assert 0 <= last <= 100
