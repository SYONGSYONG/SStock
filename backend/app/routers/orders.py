"""주문/포지션 조회 라우터."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.db.database import get_db
from app.kis.orders import cancel_order
from app.services import audit_service, order_service
from app.stocks.master import get_name

router = APIRouter(prefix="/api", tags=["orders"])


@router.get("/orders")
def list_orders(
    limit: int = Query(default=100, ge=1, le=500),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    data = order_service.list_orders(conn, limit)
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}


@router.get("/positions")
def positions(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    data = order_service.compute_positions(conn)
    for d in data:
        d["name"] = get_name(d["symbol"])
    return {"data": data}


@router.post("/orders/{order_id}/cancel")
async def cancel(order_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    row = conn.execute(
        "SELECT id, symbol, qty, kis_order_no, status FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, detail={"error": "주문 없음", "code": "NOT_FOUND"})
    if not row["kis_order_no"]:
        raise HTTPException(
            400, detail={"error": "취소할 KIS 주문번호가 없습니다", "code": "NO_ORDER_NO"}
        )
    result = await cancel_order(row["symbol"], row["kis_order_no"], row["qty"], settings=get_settings())
    if result.ok:
        order_service.update_status(conn, order_id, "cancelled")
        audit_service.log(conn, "ORDER", f"주문 #{order_id} 취소 ({row['symbol']})")
    return {"data": {"id": order_id, "cancelled": result.ok, "message": result.message}}
