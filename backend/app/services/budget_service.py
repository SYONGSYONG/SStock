"""자금/포지션 계산."""

from __future__ import annotations

import sqlite3
from typing import Any


def compute_symbol_state(
    conn: sqlite3.Connection, symbol: str, mode: str = "paper"
) -> dict[str, float]:
    """주문 이력으로 실제 보유수량/보유원가/실현손익을 계산한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    해당 모드의 주문만 집계한다.
    """
    rows = conn.execute(
        "SELECT side, filled_qty, price FROM orders "
        "WHERE symbol = ? AND mode = ? AND status NOT IN ('rejected') ORDER BY id",
        (symbol, mode),
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


def effective_ceiling(principal: int, realized_pnl: float) -> float:
    """칸막이 매수 한도 = 원금 + min(0, 실현손익).

    실현이익은 한도를 부풀리지 않고(보수적: 종이이익으로 위험을 키우지 않음), 실현손실만
    한도를 축소한다(안전). 즉 포지션을 모두 정리(flat)하면 한도는 원금으로 돌아오고,
    실현이익은 한도가 아니라 정보(누계)로만 표시한다. 손실은 계속 한도를 줄인다.
    """
    return principal + min(0.0, realized_pnl)


def get_principal(conn: sqlite3.Connection, symbol: str, mode: str = "paper") -> int | None:
    """모드별 종목 원금 한도를 조회한다."""
    row = conn.execute(
        "SELECT principal FROM capital_envelope WHERE symbol = ? AND mode = ?",
        (symbol, mode),
    ).fetchone()
    return int(row["principal"]) if row else None


def set_principal(
    conn: sqlite3.Connection, symbol: str, principal: int, mode: str = "paper"
) -> dict[str, Any]:
    """모드별 종목 원금 한도를 설정한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    conn.execute(
        "INSERT INTO capital_envelope (symbol, principal, mode) VALUES (?, ?, ?) "
        "ON CONFLICT(symbol, mode) DO UPDATE SET principal = excluded.principal",
        (symbol, principal, mode),
    )
    conn.commit()
    status = envelope_status(conn, symbol, mode=mode)
    assert status is not None
    return status


def delete_principal(conn: sqlite3.Connection, symbol: str, mode: str = "paper") -> bool:
    """모드별 종목 원금 한도를 삭제한다."""
    cur = conn.execute(
        "DELETE FROM capital_envelope WHERE symbol = ? AND mode = ?", (symbol, mode)
    )
    conn.commit()
    return cur.rowcount > 0


def envelope_status(
    conn: sqlite3.Connection, symbol: str, mode: str = "paper"
) -> dict[str, Any] | None:
    """모드별 종목의 자금 한도 상태를 반환한다. 미설정이면 None.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    principal = get_principal(conn, symbol, mode=mode)
    if principal is None:
        return None
    state = compute_symbol_state(conn, symbol, mode=mode)
    # 한도는 실현이익을 반영하지 않는다(원금 + 손실분만). 실현손익은 정보로만 표시.
    ceiling = effective_ceiling(principal, state["realized_pnl"])
    return {
        "symbol": symbol,
        "principal": principal,
        "realized_pnl": round(state["realized_pnl"]),
        "holding_cost": round(state["holding_cost"]),
        "ceiling": round(ceiling),
        "available": round(ceiling - state["holding_cost"]),
    }


def list_budgets(conn: sqlite3.Connection, mode: str = "paper") -> list[dict[str, Any]]:
    """모드별 칸막이 목록을 반환한다."""
    rows = conn.execute(
        "SELECT symbol FROM capital_envelope WHERE mode = ? ORDER BY symbol",
        (mode,),
    ).fetchall()
    result = []
    for r in rows:
        status = envelope_status(conn, r["symbol"], mode=mode)
        if status is not None:
            result.append(status)
    return result
