"""일일 주문 한도 라우터.

모드별 일일 주문 한도(횟수/금액)와 당일 사용량을 조회하고, 한도를 변경한다.
한도는 상수가 아니라 DB(risk_limit)에 저장되어 런타임에 바뀐다.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.risk_limit import RiskLimitSet
from app.services import risk_limit_service

router = APIRouter(prefix="/api/risk-limits", tags=["risk-limits"])


def _check_mode(mode: str) -> None:
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )


@router.get("")
def get_risk_limit(
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """모드별 일일 한도 + 당일 사용량을 반환한다."""
    _check_mode(mode)
    return {"data": risk_limit_service.status(conn, settings, mode)}


@router.put("")
def set_risk_limit(
    item: RiskLimitSet,
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """모드별 일일 한도를 변경한다."""
    _check_mode(mode)
    risk_limit_service.set_limits(conn, mode, item.max_orders, item.max_amount)
    return {"data": risk_limit_service.status(conn, settings, mode)}
