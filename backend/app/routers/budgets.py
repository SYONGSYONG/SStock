"""종목별 자본 칸막이 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.database import get_db
from app.schemas.budget import BudgetSet
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("")
def list_budgets(
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 자본 칸막이 목록을 반환한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    return {"data": budget_service.list_budgets(conn, mode=mode)}


@router.put("")
def set_budget(
    item: BudgetSet,
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 자본 칸막이를 설정한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    return {
        "data": budget_service.set_principal(
            conn, item.symbol, item.principal, mode=mode
        )
    }


@router.delete("/{symbol}")
def delete_budget(
    symbol: str,
    mode: str = Query(default="paper"),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 자본 칸막이를 삭제한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    if not budget_service.delete_principal(conn, symbol, mode=mode):
        raise HTTPException(404, detail={"error": "칸막이 없음", "code": "NOT_FOUND"})
    return {"data": {"symbol": symbol, "removed": True}}
