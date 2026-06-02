"""감사 로그 조회 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db.database import get_db
from app.services import audit_service

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    limit: int = Query(default=200, ge=1, le=1000),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return {"data": audit_service.list_logs(conn, limit)}
