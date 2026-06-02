"""신호 로그 저장/조회 서비스."""

from __future__ import annotations

import sqlite3
from typing import Any


def save_signal(
    conn: sqlite3.Connection,
    symbol: str,
    strategy: str,
    side: str,
    price: float | None,
    reason: str,
) -> dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO signals (symbol, strategy, side, price, reason) VALUES (?, ?, ?, ?, ?)",
        (symbol, strategy, side, price, reason),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, strategy, side, price, reason, created_at FROM signals WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def list_signals(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, symbol, strategy, side, price, reason, created_at "
        "FROM signals ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
