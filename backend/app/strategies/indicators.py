"""기술적 지표 계산 (pandas 기반)."""

from __future__ import annotations

import pandas as pd


def sma(closes: list[float], period: int) -> pd.Series:
    """단순 이동평균. 길이가 부족한 구간은 NaN."""
    if period <= 0:
        raise ValueError("period는 1 이상이어야 합니다")
    return pd.Series(closes, dtype="float64").rolling(window=period).mean()


def rsi(closes: list[float], period: int = 14) -> pd.Series:
    """RSI(상대강도지수). 0~100. 길이가 부족한 구간은 NaN."""
    if period <= 0:
        raise ValueError("period는 1 이상이어야 합니다")
    series = pd.Series(closes, dtype="float64")
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    result = 100.0 - (100.0 / (1.0 + rs))
    # loss가 0이면 rs=inf → RSI=100, gain·loss 모두 0이면 NaN 유지
    result = result.where(loss != 0, other=100.0)
    return result
