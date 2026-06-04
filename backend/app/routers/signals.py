"""신호 로그 조회 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.database import get_db
from app.services import signal_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def list_signals(
    limit: int = Query(default=100, ge=1, le=500),
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 신호 목록을 반환한다."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    data = signal_service.list_signals(conn, limit, mode=mode)
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}
