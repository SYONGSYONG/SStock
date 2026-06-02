"""관심종목 CRUD 서비스 (SQLite)."""

from __future__ import annotations

import sqlite3


def list_symbols(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, symbol, name, created_at FROM watchlist ORDER BY id"
    ).fetchall()
    return [dict(row) for row in rows]


def add_symbol(conn: sqlite3.Connection, symbol: str, name: str | None = None) -> dict:
    """관심종목을 추가한다. 중복이면 sqlite3.IntegrityError를 던진다."""
    cur = conn.execute(
        "INSERT INTO watchlist (symbol, name) VALUES (?, ?)", (symbol, name)
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, name, created_at FROM watchlist WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return dict(row)


def remove_symbol(conn: sqlite3.Connection, symbol: str) -> bool:
    """관심종목을 삭제한다. 삭제된 행이 있으면 True."""
    cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    return cur.rowcount > 0
