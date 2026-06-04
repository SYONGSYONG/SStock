"""기술적 지표 계산 (pandas 기반)."""

from __future__ import annotations

import pandas as pd


def sma(closes: list[float], period: int) -> pd.Series:
    """단순 이동평균. 길이가 부족한 구간은 NaN."""
    if period <= 0:
        raise ValueError("period는 1 이상이어야 합니다")
    return pd.Series(closes, dtype="float64").rolling(window=period).mean()


def to_tick_bars(closes: list[float], bar_ticks: int) -> list[float]:
    """원시 틱 종가열을 bar_ticks개씩 묶어 각 틱봉의 종가열로 변환한다.

    가장 최근 틱이 마지막 봉의 종가가 되도록 뒤에서부터 bar_ticks 간격으로 추출한다.
    bar_ticks<=1이면 원본 그대로(원시 틱). 틱봉 단위로 RSI·MA를 계산해 노이즈를 줄인다.
    """
    if bar_ticks <= 1:
        return list(closes)
    idxs = list(range(len(closes) - 1, -1, -bar_ticks))
    idxs.reverse()
    return [closes[i] for i in idxs]


def closed_ticks(closes: list[float], bar_ticks: int) -> list[float]:
    """진행 중(미완성) 틱봉을 제외한 '확정 구간'만 반환한다.

    `to_tick_bars`는 최신 틱에 앵커링해 매 틱 재샘플링하므로, 마지막 봉이 매 틱
    바뀌어 이동평균 교차가 경계 부근에서 출렁인다(휘프소 → 신호 폭증). 길이를
    bar_ticks의 배수로 잘라 고정 경계(완성봉의 마지막 틱)에서만 샘플링되게 한다.

    bar_ticks<=1이면 틱=봉이므로 원본 그대로 반환한다.
    """
    if bar_ticks <= 1:
        return list(closes)
    n = len(closes) - (len(closes) % bar_ticks)
    return list(closes[:n])


def rolling_sma(closes: list[float], period: int) -> list[float | None]:
    """Rolling SMA — 러닝 합계로 갱신하는 단순이동평균(최근 N개 창).

    매 지점마다 최근 N개를 다시 전부 더하지 않고, 합계에 새 값을 더하고 창을 벗어난
    값을 빼며(add-new / subtract-old) 한 번의 순회로 계산한다. pandas 전체 재계산보다
    가볍다. 길이가 부족한 구간(i < period-1)은 None.

    값은 `sma`와 동일하다(부족 구간 표기만 NaN→None).
    """
    if period <= 0:
        raise ValueError("period는 1 이상이어야 합니다")
    out: list[float | None] = [None] * len(closes)
    running = 0.0
    for i, value in enumerate(closes):
        running += value
        if i >= period:
            running -= closes[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


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
