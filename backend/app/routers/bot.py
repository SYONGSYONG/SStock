"""자동매매 봇 제어 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.bot.market_data import market_data_service
from app.bot.trading_bot import trading_bot
from app.db.database import get_db
from app.services import watchlist_service

router = APIRouter(prefix="/api/bot", tags=["bot"])


@router.get("/status")
def status() -> dict:
    return {"data": {"running": trading_bot.running, "market_running": market_data_service.running}}


@router.post("/start")
async def start(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    # 봇이 동작하려면 체결 스트림이 필요하므로 시세 수집도 함께 보장
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn)]
    await market_data_service.start(symbols)
    await trading_bot.start()
    return {"data": {"running": trading_bot.running, "market_running": market_data_service.running}}


@router.post("/stop")
async def stop() -> dict:
    # 봇만 정지(시세 수집은 유지해 시세는 계속 표시)
    await trading_bot.stop()
    return {"data": {"running": trading_bot.running}}
