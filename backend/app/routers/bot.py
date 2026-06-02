"""자동매매 봇 제어 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.bot.market_data import market_data_service
from app.bot.trading_bot import trading_bot
from app.config import Settings, get_settings
from app.db.database import get_db
from app.services import audit_service, watchlist_service

router = APIRouter(prefix="/api/bot", tags=["bot"])


class BotStartRequest(BaseModel):
    confirm_live: bool = False


@router.get("/status")
def status(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "data": {
            "running": trading_bot.running,
            "market_running": market_data_service.running,
            "mode": settings.trading_mode,
        }
    }


@router.post("/start")
async def start(
    req: BotStartRequest = BotStartRequest(),
    settings: Settings = Depends(get_settings),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    # 실전(live)은 명시적 확인 없이는 시작 불가 (안전 게이트)
    if settings.is_live and not req.confirm_live:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "실전투자 봇 시작에는 명시적 확인이 필요합니다",
                "code": "LIVE_CONFIRM_REQUIRED",
            },
        )

    # 봇이 동작하려면 체결 스트림이 필요하므로 시세 수집도 함께 보장
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn)]
    await market_data_service.start(symbols)
    await trading_bot.start()
    if settings.is_live:
        audit_service.log(conn, "MODE", "실전(LIVE) 자동매매 봇 시작 — 확인됨")
    return {
        "data": {
            "running": trading_bot.running,
            "market_running": market_data_service.running,
            "mode": settings.trading_mode,
        }
    }


@router.post("/stop")
async def stop() -> dict:
    # 봇만 정지(시세 수집은 유지해 시세는 계속 표시)
    await trading_bot.stop()
    return {"data": {"running": trading_bot.running}}
