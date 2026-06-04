"""전략 거버너 필터 테스트(확인봉·이격폭·추세 필터 + 틱사이즈)."""

from __future__ import annotations

from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.market_rules import tick_size


def _side(strat, closes):
    sig = strat.evaluate("005930", closes)
    return sig.side if sig else None


def test_틱사이즈_가격대별():
    assert tick_size(1500) == 1
    assert tick_size(3000) == 5
    assert tick_size(15000) == 10
    assert tick_size(70000) == 100
    assert tick_size(300000) == 500
    assert tick_size(600000) == 1000


def test_ma_cross_confirm_bars():
    base = [10, 9, 8, 7, 6]
    # 1봉 스파이크: confirm 1이면 매수, confirm 2면 신호 없음
    assert _side(MaCrossStrategy(2, 4, 1, confirm_bars=1), base + [20]) == "BUY"
    assert _side(MaCrossStrategy(2, 4, 1, confirm_bars=2), base + [20]) is None
    # 2봉 유지되면 confirm 2도 매수
    assert _side(MaCrossStrategy(2, 4, 1, confirm_bars=2), base + [20, 20]) == "BUY"


def test_ma_cross_diff_buffer_ticks():
    small = [100, 99, 98, 97, 96, 101]  # 단기-장기 이격 0.5(틱<1)
    big = [100, 90, 80, 70, 60, 200]  # 이격 큼
    assert _side(MaCrossStrategy(2, 4, 1, diff_buffer_ticks=0), small) == "BUY"
    # 이격폭 5틱 요구 → 살짝 교차는 무시
    assert _side(MaCrossStrategy(2, 4, 1, diff_buffer_ticks=5), small) is None
    assert _side(MaCrossStrategy(2, 4, 1, diff_buffer_ticks=5), big) == "BUY"


def test_ma_cross_trend_ma_이탈_매도():
    seq = [100, 90, 80, 70, 60, 65]  # 현재가가 추세MA(4) 아래
    assert _side(MaCrossStrategy(2, 4, 1, trend_ma=0), seq) is None
    # 추세MA 사용 시 현재가<추세MA → 추세 이탈 매도
    assert _side(MaCrossStrategy(2, 4, 1, trend_ma=4), seq) == "SELL"


def test_ma_cross_역호환_기본값():
    # 기본값(confirm 1, buffer 0, trend off)은 기존 엣지 트리거와 동일
    assert _side(MaCrossStrategy(2, 4, 1), [10, 9, 8, 7, 6, 20]) == "BUY"
    assert _side(MaCrossStrategy(2, 4, 1), [10, 11, 12, 13, 14, 2]) == "SELL"
