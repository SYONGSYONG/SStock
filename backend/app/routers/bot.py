"""자동매매 봇 제어 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.bot.registry import get_registry
from app.config import Settings, get_settings
from app.db.database import get_db
from app.services import audit_service, watchlist_service

router = APIRouter(prefix="/api/bot", tags=["bot"])


class BotStartRequest(BaseModel):
    confirm_live: bool = False


@router.get("/status")
def status(
    mode: str = Query(default="paper"),
    settings: Settings = Depends(get_settings),
) -> dict:
    """봇 상태 조회."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    registry = get_registry()
    bot = registry.get_bot(mode)
    feed = registry.get_feed(mode)
    return {
        "data": {
            "mode": mode,
            "running": bot.running,
            "market_running": feed.running,
        }
    }


@router.post("/start")
async def start(
    req: BotStartRequest = BotStartRequest(),
    mode: str = Query(default="paper"),
    settings: Settings = Depends(get_settings),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """봇 시작(모드별).

    실전(live)은 명시적 confirm_live=true + 자격증명 확인 필요.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    # 실전은 자격증명 확인
    if mode == "live":
        if not req.confirm_live:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "실전투자 봇 시작에는 명시적 확인이 필요합니다",
                    "code": "LIVE_CONFIRM_REQUIRED",
                },
            )
        if not settings.has_kis_credentials("live"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "실전투자 자격증명이 설정되지 않았습니다",
                    "code": "NO_LIVE_CREDENTIALS",
                },
            )

    registry = get_registry()
    bot = registry.get_bot(mode)
    feed = registry.get_feed(mode)

    # 봇이 동작하려면 체결 스트림이 필요하므로 시세 수집도 함께 보장
    # 해당 모드의 관심종목만 조회하여 피드 시작
    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn, mode=mode)]
    await feed.start(symbols)
    await bot.start()

    if mode == "live":
        audit_service.log(conn, "MODE", "실전(LIVE) 자동매매 봇 시작 — 확인됨")

    return {
        "data": {
            "mode": mode,
            "running": bot.running,
            "market_running": feed.running,
        }
    }


@router.post("/stop")
async def stop(mode: str = Query(default="paper")) -> dict:
    """봇 정지(모드별)."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    registry = get_registry()
    bot = registry.get_bot(mode)

    # 봇만 정지(시세 수집은 유지해 시세는 계속 표시)
    await bot.stop()

    return {"data": {"mode": mode, "running": bot.running}}
