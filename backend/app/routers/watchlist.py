"""관심종목 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.bot.market_data import market_data_service
from app.db.database import get_db
from app.schemas.watchlist import WatchCreate
from app.services import watchlist_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"data": watchlist_service.list_symbols(conn)}


async def _refresh_market_data(conn: sqlite3.Connection) -> None:
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn)]
    await market_data_service.refresh(symbols)


@router.post("", status_code=201)
async def add_watchlist(item: WatchCreate, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    # 종목명이 비어 있으면 마스터에서 자동 조회
    name = item.name or get_name(item.symbol)
    try:
        created = watchlist_service.add_symbol(conn, item.symbol, name)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "이미 등록된 종목입니다.", "code": "DUPLICATE"},
        ) from exc
    await _refresh_market_data(conn)
    return {"data": created}


@router.delete("/{symbol}")
async def remove_watchlist(symbol: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if not watchlist_service.remove_symbol(conn, symbol):
        raise HTTPException(
            status_code=404,
            detail={"error": "등록되지 않은 종목입니다.", "code": "NOT_FOUND"},
        )
    await _refresh_market_data(conn)
    return {"data": {"symbol": symbol, "removed": True}}
