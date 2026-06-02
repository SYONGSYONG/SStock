"""관심종목 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WatchItem(BaseModel):
    id: int
    symbol: str
    name: str | None = None
    created_at: str


class WatchCreate(BaseModel):
    symbol: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    name: str | None = None
