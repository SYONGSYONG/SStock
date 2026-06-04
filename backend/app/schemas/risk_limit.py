"""일일 주문 한도 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RiskLimitSet(BaseModel):
    max_orders: int = Field(ge=1, le=100_000)
    max_amount: int = Field(ge=1)
