"""시세 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class Quote(BaseModel):
    symbol: str
    price: int | None = None  # 현재가
    change: int | None = None  # 전일 대비
    change_rate: float | None = None  # 전일 대비율(%)
    sign: str | None = None  # 전일 대비 부호(1상한 2상승 3보합 4하한 5하락)
    volume: int | None = None  # 누적 거래량
    open: int | None = None
    high: int | None = None
    low: int | None = None
