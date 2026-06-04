"""주문 안전 가드.

모든 주문은 집행 전 이 가드를 통과해야 한다(절대 안전 규칙).
- 종목별 한도(수량/금액)
- 자본 칸막이 필수: 미등록 종목은 매수·매도 모두 금지(ENVELOPE_REQUIRED)
- 매수: 보유원가 + 주문금액 <= 원금 + 실현손익(ENVELOPE_EXCEEDED)
- 매도: 봇 보유 0이면 거부(NO_BOT_HOLDING), 보유 초과면 거부(SELL_EXCEEDS_HOLDING) — 기보유분 보호
- 일일 최대 주문 횟수/금액(risk_limit 테이블, 모드별; 미설정 시 DAILY_MAX_* 기본값)
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


def _bot_open_sell_qty(conn: sqlite3.Connection, symbol: str, mode: str) -> int:
    """아직 체결되지 않은 봇 매도 주문의 미체결 수량 합계.

    봇이 보유한 수량을 여러 미체결 매도로 중복 소진하는 것을 막기 위해, 매도 가능
    수량 계산 시 이 값을 차감한다. 체결/취소/거부 주문은 remaining_qty가 0이라
    자연히 제외된다.
    """
    row = conn.execute(
        "SELECT COALESCE(SUM(remaining_qty), 0) AS q FROM orders "
        "WHERE symbol = ? AND mode = ? AND side = 'SELL' "
        "AND status NOT IN ('rejected', 'cancelled')",
        (symbol, mode),
    ).fetchone()
    return int(row["q"])


def bot_sellable_qty(conn: sqlite3.Connection, symbol: str, mode: str = "paper") -> int:
    """봇이 지금 추가로 매도할 수 있는 수량.

    = 봇 보유수량(자기 주문 이력 기준) − 미체결 매도 수량. 0 이하이면 봇이 팔 것이
    없다(미보유이거나 보유분을 이미 모두 매도 대기 중). 봇은 이 값이 0 이하인 매도
    신호를 주문으로 만들지 않는다(거절 주문 폭증 방지).
    """
    from app.services import budget_service

    state = budget_service.compute_symbol_state(conn, symbol, mode=mode)
    return int(state["holding_qty"]) - _bot_open_sell_qty(conn, symbol, mode)


def check_order(
    conn: sqlite3.Connection,
    settings: Settings,
    intent: OrderIntent,
    mode: str = "paper",
) -> None:
    """위반 시 RiskError를 던진다. 통과하면 None.

    mode: 거래 모드('paper' 또는 'live'). 기본값 'paper'.
    모드별로 일일 한도/칸막이를 격리해 검증한다.
    """
    if intent.qty <= 0:
        raise RiskError("INVALID_QTY", "주문 수량은 1 이상이어야 합니다")

    order_amount = int((intent.price or 0) * intent.qty)

    # 종목별 한도
    if intent.max_qty is not None and intent.qty > intent.max_qty:
        raise RiskError(
            "SYMBOL_QTY_LIMIT", f"종목 수량 한도 초과: {intent.qty} > {intent.max_qty}"
        )
    if intent.max_amount is not None and order_amount > intent.max_amount:
        raise RiskError(
            "SYMBOL_AMOUNT_LIMIT", f"종목 금액 한도 초과: {order_amount} > {intent.max_amount}"
        )

    # 자본 칸막이(envelope) 필수: 미등록 종목은 매수·매도 모두 금지한다.
    # 봇은 명시적으로 원금을 배정한 종목만 매매하며, 등록되지 않은 종목(특히 직접
    # 매수한 기보유 종목)은 봇이 절대 건드리지 않는다.
    from app.services import budget_service

    principal = budget_service.get_principal(conn, intent.symbol, mode=mode)
    if principal is None:
        raise RiskError(
            "ENVELOPE_REQUIRED",
            f"자본 칸막이 미등록 종목은 매매할 수 없습니다: {intent.symbol}",
        )

    state = budget_service.compute_symbol_state(conn, intent.symbol, mode=mode)

    if intent.side == "BUY":
        # 매수: 보유원가 + 주문금액 <= 원금 + 실현손익
        ceiling = principal + state["realized_pnl"]
        if state["holding_cost"] + order_amount > ceiling:
            raise RiskError(
                "ENVELOPE_EXCEEDED",
                f"종목 자본 칸막이 초과: 한도 {int(ceiling)}원, "
                f"보유원가 {int(state['holding_cost'])}원 + 주문 {order_amount}원",
            )
    else:  # SELL
        # 매도: 봇이 자기 주문으로 보유한 수량까지만 허용(직접 매수한 기보유분 보호).
        bot_qty = int(state["holding_qty"])
        open_sell = _bot_open_sell_qty(conn, intent.symbol, mode)
        sellable = bot_qty - open_sell
        if bot_qty <= 0:
            # 봇이 보유하지 않은 종목 — 직접 매수한 기보유분일 수 있어 봇은 건드리지 않는다.
            raise RiskError(
                "NO_BOT_HOLDING",
                f"봇이 보유하지 않은 종목은 매도하지 않습니다(봇 보유 0주). "
                f"직접 매수한 기보유분은 봇이 매도하지 않습니다.",
            )
        if intent.qty > sellable:
            raise RiskError(
                "SELL_EXCEEDS_HOLDING",
                f"봇 매도가능 수량 초과: 매도 {intent.qty}주 > 매도가능 {sellable}주 "
                f"(봇 보유 {bot_qty}주 − 미체결 매도 {open_sell}주)",
            )

    # 일일 한도(모드별) — risk_limit 테이블에서 읽고, 없으면 settings 기본값 폴백.
    from app.services import risk_limit_service

    limits = risk_limit_service.get_limits(conn, settings, mode)

    # 일일 주문 횟수
    if risk_limit_service.today_order_count(conn, mode) >= limits["max_orders"]:
        raise RiskError(
            "DAILY_ORDER_LIMIT", f"일일 주문 횟수 한도({limits['max_orders']}) 초과"
        )

    # 일일 주문 금액
    if risk_limit_service.today_order_amount(conn, mode) + order_amount > limits["max_amount"]:
        raise RiskError(
            "DAILY_AMOUNT_LIMIT", f"일일 주문 금액 한도({limits['max_amount']}) 초과"
        )
