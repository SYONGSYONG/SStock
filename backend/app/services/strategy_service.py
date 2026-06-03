"""전략 설정 CRUD 서비스."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_config(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "symbol": row["symbol"],
        "strategy": row["strategy"],
        "params": json.loads(row["params"]) if row["params"] else {},
        "enabled": bool(row["enabled"]),
        "max_qty": row["max_qty"],
        "max_amount": row["max_amount"],
    }


def list_configs(conn: sqlite3.Connection, mode: str = "paper") -> list[dict[str, Any]]:
    """모드별 전략 설정 목록을 반환한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    """
    rows = conn.execute(
        "SELECT id, symbol, strategy, params, enabled, max_qty, max_amount "
        "FROM strategy_config WHERE mode = ? ORDER BY id",
        (mode,),
    ).fetchall()
    return [_row_to_config(r) for r in rows]


def list_enabled(conn: sqlite3.Connection, mode: str = "paper") -> list[dict[str, Any]]:
    """모드별 활성화된 전략만 반환한다."""
    return [c for c in list_configs(conn, mode=mode) if c["enabled"]]


def upsert_config(
    conn: sqlite3.Connection,
    symbol: str,
    strategy: str,
    params: dict[str, Any],
    enabled: bool = False,
    max_qty: int | None = None,
    max_amount: int | None = None,
    mode: str = "paper",
) -> dict[str, Any]:
    """(symbol, strategy, mode) 기준으로 설정을 생성하거나 갱신한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    중복 기준: (symbol, strategy, mode) 복합 UNIQUE.
    """
    conn.execute(
        """
        INSERT INTO strategy_config (symbol, strategy, params, enabled, max_qty, max_amount, mode)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, strategy, mode) DO UPDATE SET
            params = excluded.params,
            enabled = excluded.enabled,
            max_qty = excluded.max_qty,
            max_amount = excluded.max_amount
        """,
        (symbol, strategy, json.dumps(params), int(enabled), max_qty, max_amount, mode),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, strategy, params, enabled, max_qty, max_amount "
        "FROM strategy_config WHERE symbol = ? AND strategy = ? AND mode = ?",
        (symbol, strategy, mode),
    ).fetchone()
    return _row_to_config(row)


def set_enabled(conn: sqlite3.Connection, config_id: int, enabled: bool) -> bool:
    cur = conn.execute(
        "UPDATE strategy_config SET enabled = ? WHERE id = ?", (int(enabled), config_id)
    )
    conn.commit()
    return cur.rowcount > 0


def delete_config(conn: sqlite3.Connection, config_id: int) -> bool:
    cur = conn.execute("DELETE FROM strategy_config WHERE id = ?", (config_id,))
    conn.commit()
    return cur.rowcount > 0
