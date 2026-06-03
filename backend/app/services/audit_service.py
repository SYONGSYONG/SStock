"""감사/시스템 로그 서비스 (변경 불가 기록)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db.database import kst_now_str

# 카테고리: BOT | ORDER | SIGNAL | MODE | ERROR | RISK
Category = str


def log(conn: sqlite3.Connection, category: Category, message: str) -> dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO audit_logs (category, message, created_at) VALUES (?, ?, ?)",
        (category, message, kst_now_str()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, category, message, created_at FROM audit_logs WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(row)


def list_logs(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, category, message, created_at FROM audit_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
