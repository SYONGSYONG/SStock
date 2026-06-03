"""RSI + MA 추세 필터 전략 테스트."""

from __future__ import annotations

import pytest

from app.strategies.registry import build_strategy
from app.strategies.rsi_ma import RsiMaStrategy


def _uptrend_dip_recover() -> list[float]:
    """상승추세 + 끝에서 16연속 소폭 하락(RSI 과매도) + 강반등(과매도 상향 돌파).

    반등폭(6)이 하락폭(1)의 ~5.6배를 넘어야 RSI가 한 틱에 과매도선을 상향 돌파한다.
    현재가(447)는 MA50(약 422) 위에 있어 상승추세 필터를 통과한다.
    """
    base = [100.0 + 3 * i for i in range(120)]  # 강한 상승 → MA50이 멀리 아래
    dip = [base[-1] - 1.0 * k for k in range(1, 17)]  # 16연속 -1 → RSI 과매도
    return base + dip + [dip[-1] + 6.0]  # 강반등 → 과매도선 상향 돌파


def test_상승추세_과매도_반등시_매수() -> None:
    strat = RsiMaStrategy(rsi_period=14, low=30, high=70, ma_period=50)
    sig = strat.evaluate("005930", _uptrend_dip_recover())
    assert sig is not None
    assert sig.side == "BUY"
    assert "MA50" in sig.reason


def test_하락추세면_과매도_반등이어도_매수안함() -> None:
    """현재가가 MA 아래(하락추세)면 동일한 RSI 과매도 탈출이어도 매수 차단(필터)."""
    base = [500.0 - 3 * i for i in range(120)]  # 강한 하락추세 → 현재가가 MA 아래
    dip = [base[-1] - 1.0 * k for k in range(1, 17)]
    closes = base + dip + [dip[-1] + 6.0]  # RSI는 동일하게 과매도 상향 돌파하지만…
    sig = RsiMaStrategy(rsi_period=14, low=30, high=70, ma_period=50).evaluate("005930", closes)
    assert sig is None  # 현재가 < MA50 → 매수 안 함


def test_과매수_이탈시_매도() -> None:
    """RSI가 과매수선을 하향 이탈하면 추세 무관하게 매도."""
    closes = [100.0 + 3 * i for i in range(80)]  # 상승으로 RSI 과매수권(100)
    closes += [closes[-1] - 18.0]  # 큰 하락 한 방 → RSI 과매수 하향 이탈
    sig = RsiMaStrategy(rsi_period=14, low=30, high=70, ma_period=50).evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "SELL"


def test_데이터_부족시_None() -> None:
    strat = RsiMaStrategy(rsi_period=14, low=30, high=70, ma_period=50)
    assert strat.evaluate("005930", [100.0] * 10) is None


def test_잘못된_파라미터_거부() -> None:
    with pytest.raises(ValueError):
        RsiMaStrategy(rsi_period=1)
    with pytest.raises(ValueError):
        RsiMaStrategy(ma_period=1)
    with pytest.raises(ValueError):
        RsiMaStrategy(low=70, high=30)  # low >= high
    with pytest.raises(ValueError):
        RsiMaStrategy(low=0, high=70)  # low <= 0


def test_레지스트리_빌드() -> None:
    strat = build_strategy("rsi_ma", {"rsi_period": 10, "low": 25, "high": 75, "ma_period": 60})
    assert isinstance(strat, RsiMaStrategy)
    assert strat.rsi_period == 10
    assert strat.ma_period == 60
    assert strat.low == 25
    assert strat.high == 75
