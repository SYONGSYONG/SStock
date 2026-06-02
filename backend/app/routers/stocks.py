"""종목 검색 라우터 (마스터 기반, 종목명/코드 검색)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.stocks import master

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search")
def search_stocks(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    return {"data": master.search(q, limit)}
