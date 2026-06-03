"""주문 저장/조회 및 포지션 계산."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.database import kst_now_str

_FINAL_STATUSES = {"rejected", "cancelled"}


def _normalize_fill_state(
    qty: int,
    status: str,
    filled_qty: int | None = None,
    remaining_qty: int | None = None,
) -> tuple[int, int]:
    filled = qty if filled_qty is None and status == "filled" else (filled_qty or 0)
    filled = max(0, min(filled, qty))
    if remaining_qty is None:
        if status in _FINAL_STATUSES or status == "filled":
            remaining = 0
        elif status == "partial":
            remaining = max(qty - filled, 0)
        else:
            remaining = max(qty - filled, 0)
    else:
        remaining = max(0, min(remaining_qty, qty))
    return filled, remaining


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
    filled_qty: int | None = None,
    remaining_qty: int | None = None,
) -> dict[str, Any]:
    filled_qty, remaining_qty = _normalize_fill_state(qty, status, filled_qty, remaining_qty)
    cur = conn.execute(
        """
        INSERT INTO orders (
            signal_id, symbol, side, qty, filled_qty, remaining_qty, price, mode, kis_order_no, status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            signal_id,
            symbol,
            side,
            qty,
            filled_qty,
            remaining_qty,
            price,
            mode,
            kis_order_no,
            status,
            kst_now_str(),
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, signal_id, symbol, side, qty, filled_qty, remaining_qty, price, mode, kis_order_no, status, created_at "
        "FROM orders WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def update_status(
    conn: sqlite3.Connection, order_id: int, status: str, kis_order_no: str | None = None
) -> bool:
    row = conn.execute(
        "SELECT qty, filled_qty, remaining_qty FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if row is None:
        return False

    qty = int(row["qty"])
    current_filled = int(row["filled_qty"] or 0)
    current_remaining = int(row["remaining_qty"] or 0)
    if status == "filled":
        filled_qty, remaining_qty = qty, 0
    else:
        filled_qty, remaining_qty = _normalize_fill_state(
            qty,
            status,
            current_filled,
            0 if status in _FINAL_STATUSES else current_remaining,
        )

    if kis_order_no is not None:
        cur = conn.execute(
            "UPDATE orders SET status = ?, filled_qty = ?, remaining_qty = ?, kis_order_no = ? WHERE id = ?",
            (status, filled_qty, remaining_qty, kis_order_no, order_id),
        )
    else:
        cur = conn.execute(
            "UPDATE orders SET status = ?, filled_qty = ?, remaining_qty = ? WHERE id = ?",
            (status, filled_qty, remaining_qty, order_id),
        )
    conn.commit()
    return cur.rowcount > 0


def update_execution(
    conn: sqlite3.Connection,
    order_id: int,
    status: str,
    filled_qty: int,
    remaining_qty: int,
    kis_order_no: str | None = None,
) -> bool:
    if kis_order_no is not None:
        cur = conn.execute(
            "UPDATE orders SET status = ?, filled_qty = ?, remaining_qty = ?, kis_order_no = ? WHERE id = ?",
            (status, filled_qty, remaining_qty, kis_order_no, order_id),
        )
    else:
        cur = conn.execute(
            "UPDATE orders SET status = ?, filled_qty = ?, remaining_qty = ? WHERE id = ?",
            (status, filled_qty, remaining_qty, order_id),
        )
    conn.commit()
    return cur.rowcount > 0


def list_orders(conn: sqlite3.Connection, limit: int = 100, mode: str | None = None) -> list[dict[str, Any]]:
    """주문 목록을 반환한다.

    mode: 모드로 필터. 미지정 시 모든 주문.
    """
    if mode is not None:
        rows = conn.execute(
            "SELECT id, signal_id, symbol, side, qty, filled_qty, remaining_qty, price, mode, kis_order_no, status, created_at "
            "FROM orders WHERE mode = ? ORDER BY id DESC LIMIT ?",
            (mode, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, signal_id, symbol, side, qty, filled_qty, remaining_qty, price, mode, kis_order_no, status, created_at "
            "FROM orders ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def compute_positions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """실제 체결 수량만 기준으로 포지션 수량을 계산한다."""
    rows = conn.execute(
        """
        SELECT symbol,
               SUM(CASE WHEN side = 'BUY' THEN filled_qty ELSE -filled_qty END) AS net_qty
        FROM orders
        GROUP BY symbol
        HAVING net_qty <> 0
        ORDER BY symbol
        """
    ).fetchall()
    return [{"symbol": r["symbol"], "qty": r["net_qty"]} for r in rows]
