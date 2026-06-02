"""자본 칸막이 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BudgetSet(BaseModel):
    symbol: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    principal: int = Field(ge=1)
