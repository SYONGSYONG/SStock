"""자동매매 봇 엔진.

파이프라인: 실시간 체결(tick) → 종가 누적 → 활성 전략 평가 → 신호 →
            안전 가드 → 모의 주문 집행 → 감사 로그/대시보드 브로드캐스트.

안전을 위해 기본은 정지(OFF) 상태이며, 시작해야만 주문을 집행한다.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Settings, get_settings
from app.db.database import connect
from app.kis.orders import OrderResult, place_order
from app.services import audit_service, order_service, signal_service, strategy_service
from app.services.risk_guard import OrderIntent, RiskError, check_order
from app.strategies.registry import build_strategy

logger = logging.getLogger(__name__)

ConnFactory = Callable[[], sqlite3.Connection]
OrderPlacer = Callable[[str, str, int, float | None], Awaitable[OrderResult]]
Broadcaster = Callable[[dict[str, Any]], Awaitable[None]]

_DEFAULT_QTY = 1
_HISTORY_SIZE = 300


class TradingBot:
    def __init__(
        self,
        conn_factory: ConnFactory | None = None,
        settings: Settings | None = None,
        order_placer: OrderPlacer | None = None,
        broadcaster: Broadcaster | None = None,
        default_qty: int = _DEFAULT_QTY,
    ) -> None:
        self._settings = settings or get_settings()
        self._conn_factory = conn_factory or (lambda: connect(self._settings.database_path))
        self._order_placer = order_placer
        self._broadcaster = broadcaster
        self._history: dict[str, list[float]] = {}
        self._running = False
        self._default_qty = default_qty

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        self._audit("BOT", "자동매매 봇 시작")

    async def stop(self) -> None:
        self._running = False
        self._audit("BOT", "자동매매 봇 정지")

    async def on_tick(self, tick: dict[str, Any]) -> None:
        if not self._running:
            return
        symbol = tick.get("symbol")
        price = tick.get("price")
        if not symbol or price is None:
            return

        hist = self._history.setdefault(symbol, [])
        hist.append(float(price))
        if len(hist) > _HISTORY_SIZE:
            del hist[0]

        conn = self._conn_factory()
        try:
            configs = [c for c in strategy_service.list_enabled(conn) if c["symbol"] == symbol]
            for cfg in configs:
                strategy = build_strategy(cfg["strategy"], cfg["params"])
                signal = strategy.evaluate(symbol, hist)
                if signal is not None:
                    await self._handle_signal(conn, signal, cfg)
        finally:
            conn.close()

    async def _handle_signal(self, conn: sqlite3.Connection, signal: Any, cfg: dict[str, Any]) -> None:
        saved = signal_service.save_signal(
            conn, signal.symbol, signal.strategy, signal.side, signal.price, signal.reason
        )
        await self._broadcast({"type": "signal", "data": saved})

        qty = cfg.get("max_qty") or self._default_qty
        intent = OrderIntent(
            symbol=signal.symbol,
            side=signal.side,
            qty=qty,
            price=signal.price,
            max_qty=cfg.get("max_qty"),
            max_amount=cfg.get("max_amount"),
        )
        mode = self._settings.trading_mode

        try:
            check_order(conn, self._settings, intent)
        except RiskError as exc:
            audit_service.log(conn, "RISK", f"{signal.symbol} {signal.side} 주문 거부: {exc.message}")
            order = order_service.save_order(
                conn, signal.symbol, signal.side, qty, signal.price, mode,
                status="rejected", signal_id=saved["id"],
            )
            await self._broadcast({"type": "order", "data": order})
            return

        result = await self._place(signal.symbol, signal.side, qty, signal.price)
        status = "requested" if result.ok else "rejected"
        order = order_service.save_order(
            conn, signal.symbol, signal.side, qty, signal.price, mode,
            status=status, signal_id=saved["id"], kis_order_no=result.kis_order_no,
        )
        audit_service.log(
            conn, "ORDER",
            f"[{mode}] {signal.symbol} {signal.side} {qty}주 {status} ({result.message or ''})",
        )
        await self._broadcast({"type": "order", "data": order})

    async def _place(self, symbol: str, side: str, qty: int, price: float | None) -> OrderResult:
        if self._order_placer is not None:
            return await self._order_placer(symbol, side, qty, price)
        return await place_order(symbol, side, qty, price, self._settings)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        if self._broadcaster is not None:
            await self._broadcaster(message)

    def _audit(self, category: str, message: str) -> None:
        conn = self._conn_factory()
        try:
            audit_service.log(conn, category, message)
        finally:
            conn.close()


def _default_broadcaster() -> Broadcaster:
    from app.realtime.hub import hub

    async def _b(message: dict[str, Any]) -> None:
        await hub.broadcast(message)

    return _b


# 앱 전역 단일 봇 (대시보드 허브로 브로드캐스트)
trading_bot = TradingBot(broadcaster=_default_broadcaster())
