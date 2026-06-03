"""관심종목 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.bot.registry import get_registry
from app.db.database import get_db
from app.schemas.watchlist import WatchCreate
from app.services import watchlist_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 관심종목 목록을 반환한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    return {"data": watchlist_service.list_symbols(conn, mode=mode)}


async def _refresh_market_data(conn: sqlite3.Connection, mode: str) -> None:
    """해당 모드의 시세 피드를 갱신한다.

    mode: 거래 모드. 해당 모드의 관심종목만 조회하고 그 모드 피드를 refresh.
    """
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn, mode=mode)]
    feed = get_registry().get_feed(mode)
    await feed.refresh(symbols)


@router.post("", status_code=201)
async def add_watchlist(
    item: WatchCreate,
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 관심종목을 추가한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    # 종목명이 비어 있으면 마스터에서 자동 조회
    name = item.name or get_name(item.symbol)
    try:
        created = watchlist_service.add_symbol(conn, item.symbol, name, mode=mode)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "이미 등록된 종목입니다.", "code": "DUPLICATE"},
        ) from exc
    await _refresh_market_data(conn, mode)
    return {"data": created}


@router.delete("/{symbol}")
async def remove_watchlist(
    symbol: str,
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 관심종목을 삭제한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    if not watchlist_service.remove_symbol(conn, symbol, mode=mode):
        raise HTTPException(
            status_code=404,
            detail={"error": "등록되지 않은 종목입니다.", "code": "NOT_FOUND"},
        )
    await _refresh_market_data(conn, mode)
    return {"data": {"symbol": symbol, "removed": True}}
