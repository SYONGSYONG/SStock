"""지표 계산 테스트."""

from __future__ import annotations

import math

from app.strategies.indicators import rolling_sma, rsi, sma


def test_단순이동평균():
    s = sma([1, 2, 3, 4, 5], period=3)
    assert math.isnan(s.iloc[0])
    assert math.isnan(s.iloc[1])
    assert s.iloc[2] == 2.0  # (1+2+3)/3
    assert s.iloc[3] == 3.0
    assert s.iloc[4] == 4.0


def test_rolling_sma_러닝합계():
    # 부족 구간은 None, 이후는 창 평균(add-new/subtract-old로 동일 결과)
    assert rolling_sma([1, 2, 3, 4, 5], period=3) == [None, None, 2.0, 3.0, 4.0]


def test_rolling_sma_는_pandas_sma와_동일():
    closes = [10.0, 11.0, 10.5, 12.0, 11.5, 13.0, 12.5, 14.0, 9.0, 8.5]
    for period in (1, 3, 5):
        rolled = rolling_sma(closes, period)
        ref = sma(closes, period)
        for i, value in enumerate(rolled):
            if value is None:
                assert math.isnan(ref.iloc[i])
            else:
                assert abs(value - ref.iloc[i]) < 1e-9


def test_rsi_지속상승은_100에_근접():
    closes = list(range(1, 30))  # 단조 증가 → 손실 0 → RSI 100
    r = rsi(closes, period=14)
    assert r.iloc[-1] == 100.0


def test_rsi_범위():
    closes = [10, 11, 10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18]
    r = rsi(closes, period=14)
    last = r.iloc[-1]
    assert 0 <= last <= 100
