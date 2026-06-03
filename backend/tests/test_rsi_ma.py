"""RSI + MA 추세 필터 전략 테스트 (틱봉 집계 + 이중 매도)."""

from __future__ import annotations

import pytest

from app.strategies.indicators import to_tick_bars
from app.strategies.registry import build_strategy
from app.strategies.rsi_ma import RsiMaStrategy


def _strat(**kw) -> RsiMaStrategy:
    base = dict(rsi_period=14, low=30, high=70, ma_period=50, bar_ticks=1)
    base.update(kw)
    return RsiMaStrategy(**base)


def _uptrend_dip_recover() -> list[float]:
    """상승추세 + 끝에서 16연속 소폭 하락(RSI 과매도) + 강반등(과매도 상향 돌파).

    현재가(447)가 MA50(약 422) 위라 상승추세 필터를 통과한다.
    """
    base = [100.0 + 3 * i for i in range(120)]
    dip = [base[-1] - 1.0 * k for k in range(1, 17)]
    return base + dip + [dip[-1] + 6.0]


def test_상승추세_과매도_회복시_매수() -> None:
    sig = _strat().evaluate("005930", _uptrend_dip_recover())
    assert sig is not None
    assert sig.side == "BUY"
    assert "MA50" in sig.reason


def test_하락추세면_과매도_회복이어도_매수안함() -> None:
    base = [500.0 - 3 * i for i in range(120)]
    dip = [base[-1] - 1.0 * k for k in range(1, 17)]
    closes = base + dip + [dip[-1] + 6.0]
    assert _strat().evaluate("005930", closes) is None  # 현재가 < MA50 + 추세 이탈 아님


def test_RSI_과매수_이탈시_매도() -> None:
    closes = [100.0 + 3 * i for i in range(80)] + [100.0 + 3 * 79 - 18.0]
    sig = _strat().evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "SELL"
    assert "과매수" in sig.reason


def test_MA_하향돌파시_추세이탈_매도() -> None:
    """RSI가 과매수 이탈이 아니어도, 현재가가 MA를 하향 돌파하면 매도(안전장치)."""
    # 완만한 상승 후 RSI를 중립(70 아래)으로 낮춘 뒤, 마지막에 MA를 하향 돌파.
    base = [100.0 + 0.5 * i for i in range(90)]
    soft = [base[-1] - 1.0 * k for k in range(1, 7)]
    closes = base + soft + [soft[-1] - 8.0]
    sig = _strat().evaluate("005930", closes)
    assert sig is not None
    assert sig.side == "SELL"
    assert "추세 이탈" in sig.reason


def test_to_tick_bars_틱봉_집계() -> None:
    """원시 틱을 bar_ticks개씩 묶어 각 봉의 종가(가장 최근 틱)만 남긴다."""
    # 인덱스 6,3,0 → [10, 40, 70]
    assert to_tick_bars([10, 20, 30, 40, 50, 60, 70], 3) == [10.0, 40.0, 70.0]
    # bar_ticks=1이면 원본 그대로
    assert to_tick_bars([1, 2, 3], 1) == [1, 2, 3]


def test_틱봉_집계로_매수_신호() -> None:
    """각 봉 종가를 bar_ticks번 반복한 원시 틱 → 집계하면 봉열이 복원되어 동일 매수."""
    bars = _uptrend_dip_recover()
    raw: list[float] = []
    for b in bars:
        raw.extend([b] * 3)  # 각 봉을 3틱으로 확장
    sig = _strat(bar_ticks=3).evaluate("005930", raw)
    assert sig is not None
    assert sig.side == "BUY"


def test_데이터_부족시_None() -> None:
    # 50틱봉×MA50 → 약 2,550틱 필요. 그보다 적으면 None.
    assert _strat(bar_ticks=50, ma_period=50).evaluate("005930", [100.0] * 500) is None


def test_잘못된_파라미터_거부() -> None:
    with pytest.raises(ValueError):
        _strat(rsi_period=1)
    with pytest.raises(ValueError):
        _strat(ma_period=1)
    with pytest.raises(ValueError):
        _strat(bar_ticks=0)
    with pytest.raises(ValueError):
        _strat(low=70, high=30)
    with pytest.raises(ValueError):
        _strat(low=0, high=70)


def test_레지스트리_빌드() -> None:
    strat = build_strategy(
        "rsi_ma",
        {"rsi_period": 10, "low": 25, "high": 75, "ma_period": 60, "bar_ticks": 100},
    )
    assert isinstance(strat, RsiMaStrategy)
    assert strat.rsi_period == 10
    assert strat.ma_period == 60
    assert strat.bar_ticks == 100
    assert strat.low == 25
    assert strat.high == 75
