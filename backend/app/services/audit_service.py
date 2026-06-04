"""감사/시스템 로그 서비스 (변경 불가 기록, 모드별 분리)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.database import kst_now_str

# 카테고리: BOT | ORDER | SIGNAL | MODE | ERROR | RISK
Category = str


def log(
    conn: sqlite3.Connection, category: Category, message: str, mode: str = "paper"
) -> dict[str, Any]:
    """감사 로그를 모드별로 기록한다."""
    cur = conn.execute(
        "INSERT INTO audit_logs (category, message, mode, created_at) VALUES (?, ?, ?, ?)",
        (category, message, mode, kst_now_str()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, category, message, mode, created_at FROM audit_logs WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def list_logs(
    conn: sqlite3.Connection, limit: int = 200, mode: str | None = None
) -> list[dict[str, Any]]:
    """감사 로그 목록을 반환한다. mode 지정 시 해당 모드만, 미지정이면 전체."""
    if mode is not None:
        rows = conn.execute(
            "SELECT id, category, message, mode, created_at "
            "FROM audit_logs WHERE mode = ? ORDER BY id DESC LIMIT ?",
            (mode, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, category, message, mode, created_at "
            "FROM audit_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
