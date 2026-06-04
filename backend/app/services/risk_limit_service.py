"""일일 주문 한도 저장·조회 + 당일 사용량 집계.

한도(일일 주문 횟수/금액)는 상수가 아니라 모드별로 `risk_limit` 테이블에 저장한다.
행이 없으면 환경변수 기반 기본값(`settings.daily_max_*`)으로 폴백한다. 대시보드에서
런타임에 사용량을 확인하고 한도를 변경할 수 있다.

당일 집계는 risk_guard와 같은 KST 기준(`date('now','+9 hours')`)을 쓰며, 거부된 주문은
한도에서 제외한다(체결되지 않았으므로).
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.config import Settings

_MODES = ("paper", "live")


def today_order_count(conn: sqlite3.Connection, mode: str) -> int:
    """당일(KST) 거부되지 않은 주문 건수."""
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM orders "
        "WHERE mode = ? AND status NOT IN ('rejected') AND date(created_at) = date('now', '+9 hours')",
        (mode,),
    ).fetchone()
    return int(row["c"])


def today_order_amount(conn: sqlite3.Connection, mode: str) -> int:
    """당일(KST) 거부되지 않은 주문 금액 합계."""
    row = conn.execute(
        "SELECT COALESCE(SUM(qty * COALESCE(price, 0)), 0) AS s FROM orders "
        "WHERE mode = ? AND status NOT IN ('rejected') AND date(created_at) = date('now', '+9 hours')",
        (mode,),
    ).fetchone()
    return int(row["s"])


def get_limits(conn: sqlite3.Connection, settings: Settings, mode: str) -> dict[str, int]:
    """모드별 일일 한도를 반환한다. 행이 없으면 settings 기본값으로 폴백."""
    row = conn.execute(
        "SELECT max_orders, max_amount FROM risk_limit WHERE mode = ?", (mode,)
    ).fetchone()
    if row is not None:
        return {"max_orders": int(row["max_orders"]), "max_amount": int(row["max_amount"])}
    return {
        "max_orders": settings.daily_max_orders,
        "max_amount": settings.daily_max_amount,
    }


def set_limits(
    conn: sqlite3.Connection, mode: str, max_orders: int, max_amount: int
) -> dict[str, int]:
    """모드별 일일 한도를 설정(upsert)한다."""
    conn.execute(
        "INSERT INTO risk_limit (mode, max_orders, max_amount) VALUES (?, ?, ?) "
        "ON CONFLICT(mode) DO UPDATE SET max_orders = excluded.max_orders, "
        "max_amount = excluded.max_amount",
        (mode, max_orders, max_amount),
    )
    conn.commit()
    return {"max_orders": max_orders, "max_amount": max_amount}


def status(conn: sqlite3.Connection, settings: Settings, mode: str) -> dict[str, Any]:
    """모드별 일일 한도 + 당일 사용량을 함께 반환한다(대시보드 표시용)."""
    limits = get_limits(conn, settings, mode)
    return {
        "mode": mode,
        "max_orders": limits["max_orders"],
        "max_amount": limits["max_amount"],
        "order_count": today_order_count(conn, mode),
        "order_amount": today_order_amount(conn, mode),
    }
