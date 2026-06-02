"""실시간 시세 수집 제어 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.bot.market_data import market_data_service
from app.db.database import get_db
from app.realtime.hub import hub
from app.services import watchlist_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status")
def status() -> dict:
    return {
        "data": {
            "running": market_data_service.running,
            "symbols": market_data_service.symbols,
            "dashboard_clients": hub.client_count,
        }
    }


@router.post("/start")
async def start(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn)]
    await market_data_service.start(symbols)
    return {"data": {"running": market_data_service.running, "symbols": symbols}}


@router.post("/stop")
async def stop() -> dict:
    await market_data_service.stop()
    return {"data": {"running": market_data_service.running}}
