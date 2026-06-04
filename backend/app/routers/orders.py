"""주문/포지션 조회 라우터."""

from __future__ import annotations

import sqlite3

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import get_settings
from app.db.database import get_db
from app.kis.orders import AccountUnavailableError, cancel_order, get_balance
from app.services import audit_service, budget_service, order_service
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
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """포지션 조회(모드별).

    KIS 실제 잔고(직접 매수분 포함)에 봇 주문 이력 기반 보유수량을 합산해
    종목마다 봇/직접 매수 구분(source, bot_qty, manual_qty)을 부여한다.
    """
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})

    settings = get_settings()
    try:
        data = await get_balance(settings, mode=mode)
    except (httpx.HTTPError, AccountUnavailableError):
        data = []
    for d in data:
        d["name"] = get_name(d["symbol"])
        _annotate_source(conn, d, mode)
    return {"data": data}


def _annotate_source(conn: sqlite3.Connection, position: dict, mode: str) -> None:
    """포지션에 봇/직접 매수 구분 필드를 추가한다.

    봇 보유수량 = 해당 모드 주문 이력의 순매수 체결 수량(compute_symbol_state).
    실제 잔고 수량을 넘지 않도록 클램프하고, 나머지를 직접 매수분으로 본다.
    """
    total_qty = int(position.get("qty") or 0)
    bot_qty = int(budget_service.compute_symbol_state(conn, position["symbol"], mode=mode)["holding_qty"])
    bot_qty = max(0, min(bot_qty, total_qty))
    manual_qty = total_qty - bot_qty
    if bot_qty > 0 and manual_qty > 0:
        source = "mixed"
    elif bot_qty > 0:
        source = "bot"
    else:
        source = "manual"
    position["bot_qty"] = bot_qty
    position["manual_qty"] = manual_qty
    position["source"] = source


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
        audit_service.log(conn, "ORDER", f"주문 #{order_id} 취소 ({row['symbol']})", row["mode"])
    return {"data": {"id": order_id, "cancelled": result.ok, "message": result.message}}
