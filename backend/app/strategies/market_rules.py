"""한국 시장 규칙 — 호가단위(틱사이즈).

가격대별 호가단위. 이격폭(`diff_buffer_ticks`)·MA 버퍼(`ma_buffer_ticks`)·추격 거리
(`max_distance_ticks`)를 "틱 단위"로 다룰 때 쓴다. (출처: 한국거래소 호가단위, 2023 기준)
"""

from __future__ import annotations


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
