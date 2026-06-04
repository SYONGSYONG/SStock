"""자동매매 봇."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Settings, get_settings
from app.db.database import connect
from app.kis.orders import OrderResult, get_daily_ccld, place_order
from app.services import audit_service, order_service, signal_service, strategy_service
from app.services.risk_guard import OrderIntent, RiskError, bot_sellable_qty, check_order
from app.strategies.registry import build_strategy

logger = logging.getLogger(__name__)

ConnFactory = Callable[[], sqlite3.Connection]
OrderPlacer = Callable[[str, str, int, float | None], Awaitable[OrderResult]]
OrderSyncer = Callable[[str, str], Awaitable[list[dict[str, Any]]]]
Broadcaster = Callable[[dict[str, Any]], Awaitable[None]]

_DEFAULT_QTY = 1
# 틱봉 집계 전략(rsi_ma: 50틱봉×MA50 ≈ 2,550틱, 100틱봉 ≈ 5,100틱) 지원을 위해
# 원시 틱을 넉넉히 보관한다. float 6천 개라 메모리 부담은 사소하다.
_HISTORY_SIZE = 6000
_SYNC_INTERVAL_SEC = 3.0
_FINAL_STATUSES = {"rejected"}


class TradingBot:
    """자동매매 봇.

    mode: 거래 모드(paper/live). 미지정 시 settings.trading_mode.
          이 봇이 관리하는 모든 주문/신호는 이 모드로 저장된다.
    """

    def __init__(
        self,
        conn_factory: ConnFactory | None = None,
        settings: Settings | None = None,
        order_placer: OrderPlacer | None = None,
        order_syncer: OrderSyncer | None = None,
        broadcaster: Broadcaster | None = None,
        default_qty: int = _DEFAULT_QTY,
        mode: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._mode = mode or self._settings.trading_mode
        self._conn_factory = conn_factory or (lambda: connect(self._settings.database_path))
        self._order_placer = order_placer
        self._order_syncer = order_syncer
        self._broadcaster = broadcaster
        self._history: dict[str, list[float]] = {}
        # (symbol, strategy) → 직전에 발생시킨 신호 방향. 같은 방향 중복 신호를 억제한다.
        self._last_signal_side: dict[tuple[str, str], str] = {}
        self._running = False
        self._default_qty = default_qty
        self._sync_task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        if self._sync_task is None or self._sync_task.done():
            self._sync_task = asyncio.create_task(self._sync_loop())
        self._audit("BOT", "자동매매 봇 시작")

    async def stop(self) -> None:
        self._running = False
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._sync_task = None
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
            configs = [
                c
                for c in strategy_service.list_enabled(conn, mode=self._mode)
                if c["symbol"] == symbol
            ]
            for cfg in configs:
                # 알 수 없는 전략(예: 제거된 'rsi')·잘못된 파라미터는 건너뛴다(틱 처리 보호).
                try:
                    strategy = build_strategy(cfg["strategy"], cfg["params"])
                except ValueError:
                    continue
                signal = strategy.evaluate(symbol, hist)
                if signal is None:
                    continue
                # 중복 신호 억제: 직전과 같은 방향(side) 신호는 건너뛴다.
                # 확정봉 평가와 결합해 '교차 1회당 신호 1건'이 되게 한다(휘프소 폭증 방지).
                key = (symbol, cfg["strategy"])
                if self._last_signal_side.get(key) == signal.side:
                    continue
                self._last_signal_side[key] = signal.side
                await self._handle_signal(conn, signal, cfg)
        finally:
            conn.close()

    async def sync_orders(self, force: bool = False) -> list[dict[str, Any]]:
        """KIS 주문체결내역과 로컬 주문 상태를 맞춘다(자기 모드만).

        이 봇의 모드에 해당하는 주문만 동기화한다.
        """
        conn = self._conn_factory()
        updates: list[dict[str, Any]] = []
        try:
            rows = conn.execute(
                """
                SELECT id, symbol, kis_order_no, qty, filled_qty, remaining_qty, status
                FROM orders
                WHERE mode = ? AND kis_order_no IS NOT NULL AND status NOT IN ('rejected', 'filled')
                ORDER BY id
                """,
                (self._mode,),
            ).fetchall()
            for row in rows:
                order_no = row["kis_order_no"]
                if not order_no:
                    continue
                snapshots = await self._fetch_order_snapshots(row["symbol"], order_no)
                if not snapshots:
                    continue
                snapshot = self._select_snapshot(snapshots, order_no)
                if snapshot is None:
                    continue
                status = self._derive_status(row, snapshot)
                filled_qty = int(snapshot["tot_ccld_qty"])
                remaining_qty = int(snapshot["rmn_qty"])
                if (
                    status == row["status"]
                    and filled_qty == int(row["filled_qty"] or 0)
                    and remaining_qty == int(row["remaining_qty"] or 0)
                ):
                    continue
                changed = order_service.update_execution(
                    conn,
                    int(row["id"]),
                    status,
                    filled_qty,
                    remaining_qty,
                    kis_order_no=order_no,
                )
                if changed:
                    updated = conn.execute(
                        "SELECT id, signal_id, symbol, side, qty, filled_qty, remaining_qty, price, mode, kis_order_no, status, created_at "
                        "FROM orders WHERE id = ?",
                        (row["id"],),
                    ).fetchone()
                    if updated is not None:
                        payload = dict(updated)
                        updates.append(payload)
                        await self._broadcast({"type": "order", "data": payload})
            return updates
        finally:
            conn.close()

    async def _sync_loop(self) -> None:
        while self._running:
            try:
                await self.sync_orders()
            except Exception as exc:  # noqa: BLE001
                logger.warning("주문 동기화 실패: %s", exc)
            await asyncio.sleep(_SYNC_INTERVAL_SEC)

    async def _fetch_order_snapshots(self, symbol: str, order_no: str) -> list[dict[str, Any]]:
        if self._order_syncer is not None:
            return await self._order_syncer(symbol, order_no)
        return await get_daily_ccld(order_no, symbol, self._settings, mode=self._mode)

    @staticmethod
    def _select_snapshot(
        snapshots: list[dict[str, Any]],
        order_no: str,
    ) -> dict[str, Any] | None:
        for snapshot in snapshots:
            if str(snapshot.get("odno") or "") == str(order_no):
                return snapshot
        return snapshots[0] if snapshots else None

    @staticmethod
    def _derive_status(order_row: sqlite3.Row, snapshot: dict[str, Any]) -> str:
        ord_qty = int(snapshot.get("ord_qty") or order_row["qty"] or 0)
        filled_qty = int(snapshot.get("tot_ccld_qty") or 0)
        remaining_qty = int(snapshot.get("rmn_qty") or 0)
        cncl_yn = str(snapshot.get("cncl_yn") or "").upper()
        rjct_qty = int(snapshot.get("rjct_qty") or 0)

        if rjct_qty > 0:
            return "rejected"
        if cncl_yn == "Y":
            return "filled" if filled_qty >= ord_qty and remaining_qty <= 0 else "cancelled"
        if filled_qty <= 0 and remaining_qty <= 0:
            return order_row["status"]
        if remaining_qty <= 0 or filled_qty >= ord_qty:
            return "filled"
        if filled_qty > 0:
            return "partial"
        return "requested"

    async def _handle_signal(self, conn: sqlite3.Connection, signal: Any, cfg: dict[str, Any]) -> None:
        # 미보유 매도 억제: 봇이 팔 수량이 없으면(매도가능 0) 신호를 주문으로 만들지 않는다.
        # 가드(NO_BOT_HOLDING)가 어차피 거부하지만, 거절 주문/신호 폭증을 신호 단계에서 막는다.
        if signal.side == "SELL" and bot_sellable_qty(conn, signal.symbol, self._mode) <= 0:
            logger.debug("매도 신호 무시(매도가능 0): %s %s", self._mode, signal.symbol)
            return

        saved = signal_service.save_signal(
            conn, signal.symbol, signal.strategy, signal.side, signal.price, signal.reason, self._mode
        )
        await self._broadcast({"type": "signal", "data": saved, "mode": self._mode})

        qty = cfg.get("max_qty") or self._default_qty
        intent = OrderIntent(
            symbol=signal.symbol,
            side=signal.side,
            qty=qty,
            price=signal.price,
            max_qty=cfg.get("max_qty"),
            max_amount=cfg.get("max_amount"),
        )

        try:
            check_order(conn, self._settings, intent, mode=self._mode)
        except RiskError as exc:
            # 가드에서 막힌 주문은 KIS로 전송되지 않았으므로 '주문 내역(orders)'에 남기지
            # 않는다. 거절 사유는 감사 로그(RISK)에만 기록한다(진단용). 실제로 KIS에
            # 전송된 뒤 거부된 주문만 orders에 rejected로 남는다(아래 _place 경로).
            audit_service.log(
                conn, "RISK", f"{signal.symbol} {signal.side} 주문 거절: {exc.message}", self._mode
            )
            return

        result = await self._place(signal.symbol, signal.side, qty, signal.price)
        status = "requested" if result.ok else "rejected"
        order = order_service.save_order(
            conn,
            signal.symbol,
            signal.side,
            qty,
            signal.price,
            self._mode,
            status=status,
            signal_id=saved["id"],
            kis_order_no=result.kis_order_no,
        )
        audit_service.log(
            conn,
            "ORDER",
            f"[{self._mode}] {signal.symbol} {signal.side} {qty}주 {status} ({result.message or ''})",
            self._mode,
        )
        await self._broadcast({"type": "order", "data": order, "mode": self._mode})
        if result.ok:
            await self.sync_orders(force=True)

    async def _place(self, symbol: str, side: str, qty: int, price: float | None) -> OrderResult:
        if self._order_placer is not None:
            return await self._order_placer(symbol, side, qty, price)
        return await place_order(symbol, side, qty, price, self._settings, mode=self._mode)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        if self._broadcaster is not None:
            await self._broadcaster(message)

    def _audit(self, category: str, message: str) -> None:
        conn = self._conn_factory()
        try:
            audit_service.log(conn, category, message, self._mode)
        finally:
            conn.close()


def _default_broadcaster() -> Broadcaster:
    from app.realtime.hub import hub

    async def _b(message: dict[str, Any]) -> None:
        await hub.broadcast(message)

    return _b


trading_bot = TradingBot(broadcaster=_default_broadcaster())
