"""자금/포지션 계산."""

from __future__ import annotations

import sqlite3
from typing import Any


def compute_symbol_state(conn: sqlite3.Connection, symbol: str) -> dict[str, float]:
    """주문 이력으로 실제 보유수량/보유원가/실현손익을 계산한다."""
    rows = conn.execute(
        "SELECT side, filled_qty, price FROM orders "
        "WHERE symbol = ? AND status NOT IN ('rejected') ORDER BY id",
        (symbol,),
    ).fetchall()

    holding_qty = 0
    holding_cost = 0.0
    realized = 0.0
    for r in rows:
        qty = int(r["filled_qty"] or 0)
        price = float(r["price"] or 0)
        if r["side"] == "BUY":
            holding_qty += qty
            holding_cost += qty * price
        else:  # SELL
            if holding_qty <= 0:
                continue
            avg = holding_cost / holding_qty
            sell_qty = min(qty, holding_qty)
            realized += (price - avg) * sell_qty
            holding_qty -= sell_qty
            holding_cost -= avg * sell_qty

    return {
        "holding_qty": float(holding_qty),
        "holding_cost": holding_cost,
        "realized_pnl": realized,
    }


def get_principal(conn: sqlite3.Connection, symbol: str) -> int | None:
    row = conn.execute(
        "SELECT principal FROM capital_envelope WHERE symbol = ?", (symbol,)
    ).fetchone()
    return int(row["principal"]) if row else None


def set_principal(conn: sqlite3.Connection, symbol: str, principal: int) -> dict[str, Any]:
    conn.execute(
        "INSERT INTO capital_envelope (symbol, principal) VALUES (?, ?) "
        "ON CONFLICT(symbol) DO UPDATE SET principal = excluded.principal",
        (symbol, principal),
    )
    conn.commit()
    status = envelope_status(conn, symbol)
    assert status is not None
    return status


def delete_principal(conn: sqlite3.Connection, symbol: str) -> bool:
    cur = conn.execute("DELETE FROM capital_envelope WHERE symbol = ?", (symbol,))
    conn.commit()
    return cur.rowcount > 0


def envelope_status(conn: sqlite3.Connection, symbol: str) -> dict[str, Any] | None:
    """설정된 종목의 자금 한도 상태를 반환한다. 미설정이면 None."""
    principal = get_principal(conn, symbol)
    if principal is None:
        return None
    state = compute_symbol_state(conn, symbol)
    ceiling = principal + state["realized_pnl"]
    return {
        "symbol": symbol,
        "principal": principal,
        "realized_pnl": round(state["realized_pnl"]),
        "holding_cost": round(state["holding_cost"]),
        "ceiling": round(ceiling),
        "available": round(ceiling - state["holding_cost"]),
    }


def list_budgets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT symbol FROM capital_envelope ORDER BY symbol").fetchall()
    result = []
    for r in rows:
        status = envelope_status(conn, r["symbol"])
        if status is not None:
            result.append(status)
    return result
