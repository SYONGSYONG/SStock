"""주문/포지션 조회 라우터."""

from __future__ import annotations

import sqlite3

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.db.database import get_db
from app.kis.orders import cancel_order, get_balance
from app.services import audit_service, order_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api", tags=["orders"])


@router.get("/orders")
def list_orders(
    limit: int = Query(default=100, ge=1, le=500),
    mode: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """주문 목록 조회(모드별).

    mode: 모드로 필터(paper/live). 미지정 시 모든 주문.
    """
    if mode is not None and mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    data = order_service.list_orders(conn, limit, mode=mode)
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}


@router.get("/positions")
async def positions(
    mode: str = Query(default="paper"),
) -> dict:
    """포지션 조회(모드별)."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    settings = get_settings()
    try:
        data = await get_balance(settings, mode=mode)
    except httpx.HTTPError:
        data = []
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """주문 취소.

    주문의 mode를 자동 감지해 해당 모드로 취소한다.
    """
    row = conn.execute(
        "SELECT id, symbol, qty, kis_order_no, status, mode FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "주문 없음", "code": "NOT_FOUND"})
    if not row["kis_order_no"]:
        raise HTTPException(
            400,
            detail={"error": "취소할 KIS 주문번호가 없습니다", "code": "NO_ORDER_NO"},
        )
    result = await cancel_order(
        row["symbol"],
        row["kis_order_no"],
        row["qty"],
        settings=get_settings(),
        mode=row["mode"],
    )
    if result.ok:
        order_service.update_status(conn, order_id, "cancelled")
        audit_service.log(conn, "ORDER", f"주문 #{order_id} 취소 ({row['symbol']})")
    return {"data": {"id": order_id, "cancelled": result.ok, "message": result.message}}
