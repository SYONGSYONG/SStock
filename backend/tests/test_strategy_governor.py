"""전략 거버너 필터 테스트(확인봉·이격폭·추세 필터 + 틱사이즈)."""

from __future__ import annotations

from datetime import datetime

from app.strategies.ma_cross import MaCrossStrategy
from app.strategies.market_rules import (
    in_entry_block_window,
    recent_range_ticks,
    recent_turnover,
    snap_to_tick,
    stop_exit_reason,
)
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


def test_snap_to_tick_호가단위_정렬():
    # 삼성 가격대(호가단위 500): 330,750 → 331,000(가장 가까운 배수)
    assert snap_to_tick(330750) == 331000
    assert snap_to_tick(328000) == 328000  # 이미 배수면 그대로
    # 다른 가격대
    assert snap_to_tick(15123) == 15120  # 5,000~20,000 → 10원 단위
    assert snap_to_tick(1234) == 1234     # <2,000 → 1원 단위
    # None/0은 그대로(시장가 등)
    assert snap_to_tick(None) is None
    assert snap_to_tick(0) == 0


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


def test_stop_exit_reason_손절_익절_트레일링():
    # 진입가 10,000 (tick=10)
    sl = {"stop_loss_ticks": 5}  # 손절선 9,950
    assert stop_exit_reason(10000, 10000, 9940, sl) == "손절"
    assert stop_exit_reason(10000, 10000, 9960, sl) is None
    tp = {"take_profit_ticks": 10}  # 익절선 10,100
    assert stop_exit_reason(10000, 10100, 10100, tp) == "익절"
    tr = {"trailing_stop_ticks": 5}  # 최고가 10,200 → 10,150 이하
    assert stop_exit_reason(10000, 10200, 10140, tr) == "트레일링스탑"
    assert stop_exit_reason(10000, 10200, 10160, tr) is None
    # 모두 0 → 청산 없음
    assert stop_exit_reason(10000, 10200, 9000, {}) is None


def test_in_entry_block_window():
    # 장 시작(09:00) 후 5분 차단
    assert in_entry_block_window(datetime(2026, 6, 4, 9, 2), 5, 0) is True
    assert in_entry_block_window(datetime(2026, 6, 4, 9, 10), 5, 0) is False
    # 장 마감(15:30) 전 10분 차단
    assert in_entry_block_window(datetime(2026, 6, 4, 15, 25), 0, 10) is True
    assert in_entry_block_window(datetime(2026, 6, 4, 14, 0), 0, 10) is False
    # 비활성(0)
    assert in_entry_block_window(datetime(2026, 6, 4, 9, 2), 0, 0) is False


def test_recent_range_ticks():
    # 범위 100원, tick_size(9,950)=10원 → 10틱
    assert recent_range_ticks([10000, 10050, 9950], 0) == 10.0
    # 조용한 구간(모두 같음) → 0
    assert recent_range_ticks([10000] * 10, 0) == 0.0
    assert recent_range_ticks([], 5) == 0.0


def test_recent_turnover():
    # 누적거래량 100→300(증가분 200) × 평균가 1000 = 200,000
    assert recent_turnover([1000, 1000], [100, 300], 0) == 200000
    # 데이터 부족 → 0(필터 미적용)
    assert recent_turnover([1000], [100], 0) == 0.0


def test_ma_cross_역호환_기본값():
    # 기본값(confirm 1, buffer 0, trend off)은 기존 엣지 트리거와 동일
    assert _side(MaCrossStrategy(2, 4, 1), [10, 9, 8, 7, 6, 20]) == "BUY"
    assert _side(MaCrossStrategy(2, 4, 1), [10, 11, 12, 13, 14, 2]) == "SELL"
