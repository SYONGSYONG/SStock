"""종목별 자본 칸막이(capital envelope) 서비스.

칸막이 한도 = 원금(principal) + 실현손익(realized P&L, 평균원가 기준).
매수는 보유원가 + 주문금액 <= 한도 일 때만 허용한다(가드는 risk_guard에서).
실현손익은 매도로 확정된 손익만 반영하며, 손실이면 한도도 줄어든다.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# 포지션/원가에 반영하지 않는 주문 상태
_INACTIVE = ("rejected", "cancelled")


def compute_symbol_state(conn: sqlite3.Connection, symbol: str) -> dict[str, float]:
    """주문 이력으로 종목의 보유수량·보유원가·실현손익을 평균원가법으로 계산한다."""
    rows = conn.execute(
        "SELECT side, qty, price FROM orders "
        "WHERE symbol = ? AND status NOT IN ('rejected','cancelled') ORDER BY id",
        (symbol,),
    ).fetchall()

    holding_qty = 0
    holding_cost = 0.0
    realized = 0.0
    for r in rows:
        qty = int(r["qty"])
        price = float(r["price"] or 0)
        if r["side"] == "BUY":
            holding_qty += qty
            holding_cost += qty * price
        else:  # SELL
            if holding_qty <= 0:
                continue  # 보유분 없는 매도는 원가 계산에서 제외
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
    """칸막이가 설정된 종목의 한도/가용 현황. 미설정이면 None."""
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
