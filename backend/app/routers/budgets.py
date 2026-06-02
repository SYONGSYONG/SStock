"""종목별 자본 칸막이 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.schemas.budget import BudgetSet
from app.services import budget_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("")
def list_budgets(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"data": budget_service.list_budgets(conn)}


@router.put("")
def set_budget(item: BudgetSet, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"data": budget_service.set_principal(conn, item.symbol, item.principal)}


@router.delete("/{symbol}")
def delete_budget(symbol: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if not budget_service.delete_principal(conn, symbol):
        raise HTTPException(404, detail={"error": "칸막이 없음", "code": "NOT_FOUND"})
    return {"data": {"symbol": symbol, "removed": True}}
