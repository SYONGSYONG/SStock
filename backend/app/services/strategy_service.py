"""전략 설정 CRUD 서비스."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.services import audit_service


def _enabled_label(enabled: bool) -> str:
    return "ON" if enabled else "OFF"


def _change_message(
    symbol: str,
    strategy: str,
    old: dict[str, Any] | None,
    new: dict[str, Any],
    source: str,
) -> str | None:
    """전략 설정 변경을 사람이 읽을 수 있는 한 줄로 요약한다.

    old가 None이면 신규 등록, 아니면 before→after diff. 실제 변경이 없으면 None
    (감사 로그를 남기지 않음). source는 변경 주체(예: "사용자", "오토모드")로,
    사후에 자동·수동을 구분하기 위한 핵심 필드다.
    """
    if old is None:
        return (
            f"{symbol} [{strategy}] 전략 등록({source}) · {_enabled_label(new['enabled'])}"
        )

    parts: list[str] = []
    old_params, new_params = old["params"], new["params"]
    for key in sorted(set(old_params) | set(new_params)):
        if old_params.get(key) != new_params.get(key):
            parts.append(f"{key} {old_params.get(key)}→{new_params.get(key)}")
    if old["enabled"] != new["enabled"]:
        parts.append(
            f"enabled {_enabled_label(old['enabled'])}→{_enabled_label(new['enabled'])}"
        )
    if old["max_qty"] != new["max_qty"]:
        parts.append(f"max_qty {old['max_qty']}→{new['max_qty']}")
    if old["max_amount"] != new["max_amount"]:
        parts.append(f"max_amount {old['max_amount']}→{new['max_amount']}")

    if not parts:
        return None
    return f"{symbol} [{strategy}] 전략 변경({source}) · " + ", ".join(parts)


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
    source: str = "사용자",
) -> dict[str, Any]:
    """(symbol, strategy, mode) 기준으로 설정을 생성하거나 갱신한다.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    중복 기준: (symbol, strategy, mode) 복합 UNIQUE.
    source: 변경 주체("사용자"=수동, "오토모드" 등=자동). 감사 로그에 남겨
        사후에 자동·수동 전략전환을 구분할 수 있게 한다. 기본값은 수동.
    """
    existing = conn.execute(
        "SELECT id, symbol, strategy, params, enabled, max_qty, max_amount "
        "FROM strategy_config WHERE symbol = ? AND strategy = ? AND mode = ?",
        (symbol, strategy, mode),
    ).fetchone()
    old = _row_to_config(existing) if existing else None

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
    config = _row_to_config(row)

    message = _change_message(symbol, strategy, old, config, source)
    if message is not None:
        audit_service.log(conn, "STRATEGY", message, mode)
    return config


def set_enabled(
    conn: sqlite3.Connection,
    config_id: int,
    enabled: bool,
    source: str = "사용자",
) -> bool:
    """전략 활성화 여부를 토글하고 변경을 감사 로그에 남긴다.

    source: 변경 주체("사용자"=수동, "오토모드" 등=자동). upsert_config와 동일.
    """
    row = conn.execute(
        "SELECT symbol, strategy, enabled, mode FROM strategy_config WHERE id = ?",
        (config_id,),
    ).fetchone()
    if row is None:
        return False

    cur = conn.execute(
        "UPDATE strategy_config SET enabled = ? WHERE id = ?", (int(enabled), config_id)
    )
    conn.commit()
    if cur.rowcount > 0 and bool(row["enabled"]) != enabled:
        state = f"{_enabled_label(bool(row['enabled']))}→{_enabled_label(enabled)}"
        audit_service.log(
            conn,
            "STRATEGY",
            f"{row['symbol']} [{row['strategy']}] 전략 {state}({source})",
            row["mode"],
        )
    return cur.rowcount > 0


def delete_config(conn: sqlite3.Connection, config_id: int) -> bool:
    cur = conn.execute("DELETE FROM strategy_config WHERE id = ?", (config_id,))
    conn.commit()
    return cur.rowcount > 0
