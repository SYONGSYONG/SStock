"""전략 설정 스키마."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StrategyConfigCreate(BaseModel):
    symbol: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    strategy: Literal["ma_cross", "rsi_ma"]
    params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = False
    max_qty: int | None = Field(default=None, ge=1)
    max_amount: int | None = Field(default=None, ge=1)


class EnabledUpdate(BaseModel):
    enabled: bool


class StrategyConfig(BaseModel):
    id: int
    symbol: str
    strategy: str
    params: dict[str, Any]
    enabled: bool
    max_qty: int | None = None
    max_amount: int | None = None
