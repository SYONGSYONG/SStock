"""신호 로그 조회 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db.database import get_db
from app.services import signal_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("")
def list_signals(
    limit: int = Query(default=100, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    data = signal_service.list_signals(conn, limit)
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}
