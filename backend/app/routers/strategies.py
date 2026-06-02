"""전략 설정 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.schemas.strategy import EnabledUpdate, StrategyConfigCreate
from app.services import strategy_service
from app.strategies.registry import build_strategy

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_strategies(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"data": strategy_service.list_configs(conn)}


@router.post("", status_code=201)
def upsert_strategy(
    item: StrategyConfigCreate, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    # 파라미터 유효성: 전략 인스턴스 생성으로 검증(short<long, RSI 범위 등)
    try:
        build_strategy(item.strategy, item.params)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": str(exc), "code": "INVALID_PARAMS"}
        ) from exc
    created = strategy_service.upsert_config(
        conn,
        item.symbol,
        item.strategy,
        item.params,
        item.enabled,
        item.max_qty,
        item.max_amount,
    )
    return {"data": created}


@router.patch("/{config_id}/enabled")
def set_enabled(
    config_id: int, body: EnabledUpdate, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    if not strategy_service.set_enabled(conn, config_id, body.enabled):
        raise HTTPException(404, detail={"error": "설정 없음", "code": "NOT_FOUND"})
    return {"data": {"id": config_id, "enabled": body.enabled}}


@router.delete("/{config_id}")
def delete_strategy(config_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if not strategy_service.delete_config(conn, config_id):
        raise HTTPException(404, detail={"error": "설정 없음", "code": "NOT_FOUND"})
    return {"data": {"id": config_id, "removed": True}}
