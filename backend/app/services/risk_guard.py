"""주문 안전 가드.

모든 주문은 집행 전 이 가드를 통과해야 한다(절대 안전 규칙).
- 일일 최대 주문 횟수
- 일일 최대 주문 금액
- 종목별 한도(수량/금액)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.config import Settings

_INACTIVE = ("rejected",)


class RiskError(Exception):
    """가드 위반. code로 사유를 식별한다."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    qty: int
    price: float | None
    max_qty: int | None = None
    max_amount: int | None = None


def _today_order_count(conn: sqlite3.Connection, mode: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM orders "
        "WHERE mode = ? AND status NOT IN ('rejected') AND date(created_at) = date('now')",
        (mode,),
    ).fetchone()
    return int(row["c"])


def _today_order_amount(conn: sqlite3.Connection, mode: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(qty * COALESCE(price, 0)), 0) AS s FROM orders "
        "WHERE mode = ? AND status NOT IN ('rejected') AND date(created_at) = date('now')",
        (mode,),
    ).fetchone()
    return int(row["s"])


def check_order(conn: sqlite3.Connection, settings: Settings, intent: OrderIntent) -> None:
    """위반 시 RiskError를 던진다. 통과하면 None."""
    if intent.qty <= 0:
        raise RiskError("INVALID_QTY", "주문 수량은 1 이상이어야 합니다")

    order_amount = int((intent.price or 0) * intent.qty)
    mode = settings.trading_mode

    # 종목별 한도
    if intent.max_qty is not None and intent.qty > intent.max_qty:
        raise RiskError(
            "SYMBOL_QTY_LIMIT", f"종목 수량 한도 초과: {intent.qty} > {intent.max_qty}"
        )
    if intent.max_amount is not None and order_amount > intent.max_amount:
        raise RiskError(
            "SYMBOL_AMOUNT_LIMIT", f"종목 금액 한도 초과: {order_amount} > {intent.max_amount}"
        )

    # 종목별 자본 칸막이(envelope): 매수 시 보유원가 + 주문금액 <= 원금 + 실현손익
    if intent.side == "BUY":
        from app.services import budget_service

        principal = budget_service.get_principal(conn, intent.symbol)
        if principal is not None:
            state = budget_service.compute_symbol_state(conn, intent.symbol)
            ceiling = principal + state["realized_pnl"]
            if state["holding_cost"] + order_amount > ceiling:
                raise RiskError(
                    "ENVELOPE_EXCEEDED",
                    f"종목 자본 칸막이 초과: 한도 {int(ceiling)}원, "
                    f"보유원가 {int(state['holding_cost'])}원 + 주문 {order_amount}원",
                )

    # 일일 주문 횟수
    if _today_order_count(conn, mode) >= settings.daily_max_orders:
        raise RiskError(
            "DAILY_ORDER_LIMIT", f"일일 주문 횟수 한도({settings.daily_max_orders}) 초과"
        )

    # 일일 주문 금액
    if _today_order_amount(conn, mode) + order_amount > settings.daily_max_amount:
        raise RiskError(
            "DAILY_AMOUNT_LIMIT", f"일일 주문 금액 한도({settings.daily_max_amount}) 초과"
        )
