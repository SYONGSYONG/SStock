"""신호 로그 저장/조회 서비스(모드별 분리)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.database import kst_now_str


def save_signal(
    conn: sqlite3.Connection,
    symbol: str,
    strategy: str,
    side: str,
    price: float | None,
    reason: str,
    mode: str,
    observe: bool = False,
) -> dict[str, Any]:
    """신호를 모드별로 저장한다.

    observe=True면 OFF(비활성) 전략의 '관찰 전용' 신호다(실주문과 연동되지 않음).
    """
    cur = conn.execute(
        "INSERT INTO signals (symbol, strategy, side, price, reason, mode, observe, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, strategy, side, price, reason, mode, int(observe), kst_now_str()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, strategy, side, price, reason, mode, observe, created_at "
        "FROM signals WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def list_signals(
    conn: sqlite3.Connection, limit: int = 100, mode: str | None = None
) -> list[dict[str, Any]]:
    """신호 목록을 반환한다. mode 지정 시 해당 모드만, 미지정이면 전체."""
    if mode is not None:
        rows = conn.execute(
            "SELECT id, symbol, strategy, side, price, reason, mode, observe, created_at "
            "FROM signals WHERE mode = ? ORDER BY id DESC LIMIT ?",
            (mode, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, symbol, strategy, side, price, reason, mode, observe, created_at "
            "FROM signals ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
