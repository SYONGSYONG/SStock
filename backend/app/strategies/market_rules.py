"""한국 시장 규칙 — 호가단위(틱사이즈).

가격대별 호가단위. 이격폭(`diff_buffer_ticks`)·MA 버퍼(`ma_buffer_ticks`)·추격 거리
(`max_distance_ticks`)를 "틱 단위"로 다룰 때 쓴다. (출처: 한국거래소 호가단위, 2023 기준)
"""

from __future__ import annotations

from datetime import datetime

# KRX 정규장(분 단위, 09:00~15:30)
_OPEN_MIN = 9 * 60
_CLOSE_MIN = 15 * 60 + 30


def tick_size(price: float) -> int:
    """가격에 따른 호가단위(원)를 반환한다.

    ~2,000:1 / ~5,000:5 / ~20,000:10 / ~50,000:50 / ~200,000:100 / ~500,000:500 / 그 이상:1,000
    """
    if price < 2000:
        return 1
    if price < 5000:
        return 5
    if price < 20000:
        return 10
    if price < 50000:
        return 50
    if price < 200000:
        return 100
    if price < 500000:
        return 500
    return 1000


def snap_to_tick(price: float | None) -> float | None:
    """가격을 호가단위(tick_size) 배수로 반올림한다(KRX 호가단위 위반 거절 방지).

    예: 330,750(삼성 가격대 호가단위 500) → 331,000. price가 None/0 이하이면 그대로 반환
    (시장가 등). 반환은 정수 원 단위.
    """
    if price is None or price <= 0:
        return price
    ts = tick_size(price)
    return float(round(price / ts) * ts)


def stop_exit_reason(
    entry_price: float, high_price: float, cur_price: float, params: dict
) -> str | None:
    """보유 중 보호 청산(손절/익절/트레일링) 사유. 해당 없으면 None.

    틱 단위로 판정한다. 0이면 해당 청산 비활성. 손절·익절·트레일링은 전략 신호와
    무관하게 즉시 처리한다(최소보유/쿨다운 무시).
    - stop_loss_ticks: 진입가 − tick×N 이하 → 손절
    - take_profit_ticks: 진입가 + tick×N 이상 → 익절
    - trailing_stop_ticks: (이익 구간에서) 최고가 − tick×N 이하 → 트레일링스탑
    """
    ts = tick_size(cur_price)
    sl = int(params.get("stop_loss_ticks", 0) or 0)
    tp = int(params.get("take_profit_ticks", 0) or 0)
    tr = int(params.get("trailing_stop_ticks", 0) or 0)
    if sl > 0 and cur_price <= entry_price - ts * sl:
        return "손절"
    if tp > 0 and cur_price >= entry_price + ts * tp:
        return "익절"
    if tr > 0 and high_price > entry_price and (high_price - cur_price) >= ts * tr:
        return "트레일링스탑"
    return None


def recent_range_ticks(closes: list[float], lookback: int) -> float:
    """최근 lookback개 틱의 (고가−저가)를 호가단위(틱) 수로 환산. 변동성 필터용.

    너무 조용한 횡보 구간(범위가 작음)에서 매매를 피하기 위해 쓴다.
    """
    if not closes:
        return 0.0
    window = closes[-lookback:] if lookback > 0 else closes
    if not window:
        return 0.0
    rng = max(window) - min(window)
    return rng / tick_size(window[-1])


def recent_turnover(closes: list[float], volumes: list[float], lookback: int) -> float:
    """최근 lookback개 틱의 거래대금 추정(누적거래량 증가분 × 평균가). 거래대금 필터용.

    volumes는 누적 거래량(acml_vol). 데이터가 부족하면 0.0(필터 미적용 의미).
    """
    if len(volumes) < 2 or not closes:
        return 0.0
    vw = volumes[-lookback:] if lookback > 0 else volumes
    cw = closes[-lookback:] if lookback > 0 else closes
    if len(vw) < 2 or not cw:
        return 0.0
    delta_vol = max(vw[-1] - vw[0], 0.0)  # 누적이라 증가분
    avg_price = sum(cw) / len(cw)
    return delta_vol * avg_price


def in_entry_block_window(now: datetime, after_open_min: int, before_close_min: int) -> bool:
    """장 시작 직후/마감 직전 '신규 진입 금지' 시간대면 True.

    after_open_min: 장 시작(09:00) 후 N분 진입 금지. before_close_min: 장 마감(15:30) 전 N분 금지.
    값이 0이면 해당 차단 비활성.
    """
    minutes = now.hour * 60 + now.minute + now.second / 60
    if after_open_min > 0 and _OPEN_MIN <= minutes < _OPEN_MIN + after_open_min:
        return True
    if before_close_min > 0 and _CLOSE_MIN - before_close_min < minutes <= _CLOSE_MIN:
        return True
    return False
