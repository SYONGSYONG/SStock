"""실시간 시세 수집 제어 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.bot.registry import get_registry
from app.db.database import get_db
from app.realtime.hub import hub
from app.services import watchlist_service

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status")
def status(mode: str = Query(default="paper")) -> dict:
    """시세 수집 상태 조회."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    registry = get_registry()
    feed = registry.get_feed(mode)
    return {
        "data": {
            "mode": mode,
            "running": feed.running,
            "symbols": feed.symbols,
            "dashboard_clients": hub.client_count,
        }
    }


@router.post("/start")
async def start(mode: str = Query(default="paper"), conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """시세 수집 시작."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    registry = get_registry()
    feed = registry.get_feed(mode)

    symbols = [row["symbol"] for row in watchlist_service.list_symbols(conn)]
    if feed.running:
        await feed.refresh(symbols)
    else:
        await feed.start(symbols)
    return {"data": {"mode": mode, "running": feed.running, "symbols": symbols}}


@router.post("/stop")
async def stop(mode: str = Query(default="paper")) -> dict:
    """시세 수집 정지."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    registry = get_registry()
    feed = registry.get_feed(mode)

    await feed.stop()
    return {"data": {"mode": mode, "running": feed.running}}
