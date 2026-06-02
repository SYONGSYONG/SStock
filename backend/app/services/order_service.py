"""주문 저장/조회 및 포지션 계산."""

from __future__ import annotations

import sqlite3
from typing import Any

# 포지션에 반영되지 않는 상태(거부/취소)
_INACTIVE_STATUSES = ("rejected", "cancelled")


def save_order(
    conn: sqlite3.Connection,
    symbol: str,
    side: str,
    qty: int,
    price: float | None,
    mode: str,
    status: str,
    signal_id: int | None = None,
    kis_order_no: str | None = None,
) -> dict[str, Any]:
    cur = conn.execute(
        """
        INSERT INTO orders (signal_id, symbol, side, qty, price, mode, kis_order_no, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (signal_id, symbol, side, qty, price, mode, kis_order_no, status),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, signal_id, symbol, side, qty, price, mode, kis_order_no, status, created_at "
        "FROM orders WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def update_status(
    conn: sqlite3.Connection, order_id: int, status: str, kis_order_no: str | None = None
) -> bool:
    if kis_order_no is not None:
        cur = conn.execute(
            "UPDATE orders SET status = ?, kis_order_no = ? WHERE id = ?",
            (status, kis_order_no, order_id),
        )
    else:
        cur = conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    return cur.rowcount > 0


def list_orders(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, signal_id, symbol, side, qty, price, mode, kis_order_no, status, created_at "
        "FROM orders ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def compute_positions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """거부/취소를 제외한 주문으로 종목별 순보유수량을 계산한다."""
    placeholders = ",".join("?" for _ in _INACTIVE_STATUSES)
    rows = conn.execute(
        f"""
        SELECT symbol,
               SUM(CASE WHEN side = 'BUY' THEN qty ELSE -qty END) AS net_qty
        FROM orders
        WHERE status NOT IN ({placeholders})
        GROUP BY symbol
        HAVING net_qty <> 0
        ORDER BY symbol
        """,
        _INACTIVE_STATUSES,
    ).fetchall()
    return [{"symbol": r["symbol"], "qty": r["net_qty"]} for r in rows]
