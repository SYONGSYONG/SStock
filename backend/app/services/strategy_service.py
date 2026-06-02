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


def list_configs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, symbol, strategy, params, enabled, max_qty, max_amount "
        "FROM strategy_config ORDER BY id"
    ).fetchall()
    return [_row_to_config(r) for r in rows]


def list_enabled(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [c for c in list_configs(conn) if c["enabled"]]


def upsert_config(
    conn: sqlite3.Connection,
    symbol: str,
    strategy: str,
    params: dict[str, Any],
    enabled: bool = False,
    max_qty: int | None = None,
    max_amount: int | None = None,
) -> dict[str, Any]:
    """(symbol, strategy) 기준으로 설정을 생성하거나 갱신한다."""
    conn.execute(
        """
        INSERT INTO strategy_config (symbol, strategy, params, enabled, max_qty, max_amount)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, strategy) DO UPDATE SET
            params = excluded.params,
            enabled = excluded.enabled,
            max_qty = excluded.max_qty,
            max_amount = excluded.max_amount
        """,
        (symbol, strategy, json.dumps(params), int(enabled), max_qty, max_amount),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, symbol, strategy, params, enabled, max_qty, max_amount "
        "FROM strategy_config WHERE symbol = ? AND strategy = ?",
        (symbol, strategy),
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
