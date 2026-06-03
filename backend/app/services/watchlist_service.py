"""관심종목 CRUD 서비스 (SQLite)."""

from __future__ import annotations

import sqlite3


def list_symbols(conn: sqlite3.Connection, mode: str = "paper") -> list[dict]:
    """모드별 관심종목 목록을 반환한다."""
    rows = conn.execute(
        "SELECT id, symbol, name, created_at FROM watchlist WHERE mode = ? ORDER BY id",
        (mode,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_symbol(
    conn: sqlite3.Connection, symbol: str, name: str | None = None, mode: str = "paper"
) -> dict:
    """관심종목을 추가한다. 중복이면 sqlite3.IntegrityError를 던진다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    중복 기준: (symbol, mode) 복합 UNIQUE.
    """
    cur = conn.execute(
        "INSERT INTO watchlist (symbol, name, mode) VALUES (?, ?, ?)",
        (symbol, name, mode),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, name, created_at FROM watchlist WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def remove_symbol(conn: sqlite3.Connection, symbol: str, mode: str = "paper") -> bool:
    """관심종목을 삭제한다. 삭제된 행이 있으면 True.

    mode: 거래 모드. 기본값 'paper'.
    """
    cur = conn.execute(
        "DELETE FROM watchlist WHERE symbol = ? AND mode = ?", (symbol, mode)
    )
    conn.commit()
    return cur.rowcount > 0


def backfill_names(conn: sqlite3.Connection, resolver) -> int:
    """모든 모드에서 종목명이 비어 있는 관심종목을 resolver(symbol)->name 으로 채운다.

    모드 무관으로 전체를 처리한다(종목명은 모드 공유 정보).
    """
    rows = conn.execute(
        "SELECT id, symbol FROM watchlist WHERE name IS NULL OR name = ''"
    ).fetchall()
    filled = 0
    for row in rows:
        name = resolver(row["symbol"])
        if name:
            conn.execute("UPDATE watchlist SET name = ? WHERE id = ?", (name, row["id"]))
            filled += 1
    if filled:
        conn.commit()
    return filled
