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
from app.services import (
    audit_service,
    order_service,
    risk_limit_service,
    signal_service,
    strategy_service,
)
from app.services.risk_guard import OrderIntent, RiskError, bot_sellable_qty, check_order
from app.strategies.base import Signal
from app.strategies.market_rules import (
    in_entry_block_window,
    recent_range_ticks,
    recent_turnover,
    stop_exit_reason,
    tick_size,
)
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
        # 종목별 누적 거래량(acml_vol) 히스토리 — 거래대금 필터용(틱에 volume이 있을 때만).
        self._vol_history: dict[str, list[float]] = {}
        # 종목별 최신 스프레드(최우선 매도호가 − 매수호가, 원) — 호가 구독에서 갱신.
        self._spread: dict[str, int] = {}
        # (symbol, strategy) → 직전에 발생시킨 신호 방향. 같은 방향 중복 신호를 억제한다.
        self._last_signal_side: dict[tuple[str, str], str] = {}
        # 거버너 상태: (symbol, strategy) → 매수/매도가 일어난 확정봉 인덱스(최소보유·쿨다운용).
        self._entry_bar: dict[tuple[str, str], int] = {}
        self._exit_bar: dict[tuple[str, str], int] = {}
        # 보호 청산용: 진입가 / 진입 후 최고가(손절·익절·트레일링 판정).
        self._entry_price: dict[tuple[str, str], float] = {}
        self._high_price: dict[tuple[str, str], float] = {}
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
        # 호가 메시지: 스프레드만 갱신하고 종료(전략 평가 대상 아님).
        if tick.get("kind") == "orderbook":
            sym = tick.get("symbol")
            ask = tick.get("ask")
            bid = tick.get("bid")
            if sym and ask and bid and ask > 0 and bid > 0:
                self._spread[sym] = int(ask) - int(bid)
            return
        symbol = tick.get("symbol")
        price = tick.get("price")
        if not symbol or price is None:
            return

        hist = self._history.setdefault(symbol, [])
        hist.append(float(price))
        if len(hist) > _HISTORY_SIZE:
            del hist[0]

        vol = tick.get("volume")
        if vol is not None:
            vh = self._vol_history.setdefault(symbol, [])
            vh.append(float(vol))
            if len(vh) > _HISTORY_SIZE:
                del vh[0]

        conn = self._conn_factory()
        try:
            configs = [
                c
                for c in strategy_service.list_enabled(conn, mode=self._mode)
                if c["symbol"] == symbol
            ]
            for cfg in configs:
                key = (symbol, cfg["strategy"])
                # 0) 보호 청산(손절/익절/트레일링): 보유 중이면 전략 신호와 무관하게 즉시 검사.
                if await self._check_stops(conn, key, symbol, float(price), hist, cfg):
                    continue
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
                if self._last_signal_side.get(key) == signal.side:
                    continue
                # 실전 거버너: 쿨다운/최소보유/미체결매수/하루손실/시간 게이트.
                if not self._governor_allows(conn, key, signal.side, hist, cfg):
                    continue
                self._last_signal_side[key] = signal.side
                placed = await self._handle_signal(conn, signal, cfg)
                bar = self._bar_index(hist, cfg)
                if placed == "BUY":
                    self._entry_bar[key] = bar
                    self._entry_price[key] = float(signal.price or price)
                    self._high_price[key] = float(signal.price or price)
                elif placed == "SELL":
                    self._exit_bar[key] = bar
                    self._entry_bar.pop(key, None)
                    self._entry_price.pop(key, None)
                    self._high_price.pop(key, None)
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

    @staticmethod
    def _bar_index(hist: list[float], cfg: dict[str, Any]) -> int:
        """현재 확정봉 인덱스 = 히스토리 길이 // bar_ticks(거버너 봉 수 측정용)."""
        bt = int(cfg.get("params", {}).get("bar_ticks", 50)) or 1
        return len(hist) // bt

    def _has_open_buy(self, conn: sqlite3.Connection, symbol: str) -> bool:
        """미체결 매수 주문(requested/partial)이 있으면 True(신규 매수 중복 방지)."""
        row = conn.execute(
            "SELECT 1 FROM orders WHERE symbol = ? AND mode = ? AND side = 'BUY' "
            "AND status IN ('requested', 'partial') LIMIT 1",
            (symbol, self._mode),
        ).fetchone()
        return row is not None

    def _governor_allows(
        self,
        conn: sqlite3.Connection,
        key: tuple[str, str],
        side: str,
        hist: list[float],
        cfg: dict[str, Any],
    ) -> bool:
        """실전 거버너 게이트. 통과하면 True.

        - 매수: 매도 후 cooldown_bars 동안 금지, 미체결 매수 있으면 금지.
        - 매도: 매수 후 min_hold_bars 동안 (일반)매도 금지.
        값이 0이면 해당 게이트는 무시(현행 동작).
        """
        params = cfg.get("params", {})
        bar = self._bar_index(hist, cfg)
        if side == "BUY":
            cooldown = int(params.get("cooldown_bars", 0))
            exit_bar = self._exit_bar.get(key)
            if cooldown > 0 and exit_bar is not None and bar - exit_bar < cooldown:
                return False  # 쿨다운 중
            if self._has_open_buy(conn, key[0]):
                return False  # 미체결 매수 중복 방지
            if self._entry_blocked(conn):
                return False  # 하루 손실 한도 초과 또는 진입 금지 시간대
            # 시장 상태 필터(변동성/거래대금) — 최근 ~20봉 기준
            lookback = (int(params.get("bar_ticks", 50)) or 1) * 20
            mv = int(params.get("min_volatility_ticks", 0))
            if mv > 0 and recent_range_ticks(hist, lookback) < mv:
                return False  # 너무 조용한 구간(변동성 부족)
            mt = int(params.get("min_turnover", 0))
            if mt > 0:
                vh = self._vol_history.get(key[0], [])
                if len(vh) >= 2 and recent_turnover(hist, vh, lookback) < mt:
                    return False  # 거래대금 부족
            ms = int(params.get("max_spread_ticks", 0))
            if ms > 0 and hist:
                spread = self._spread.get(key[0])
                if spread is not None and spread > tick_size(hist[-1]) * ms:
                    return False  # 스프레드 과대(들어가자마자 손실 위험)
            return True
        # SELL
        min_hold = int(params.get("min_hold_bars", 0))
        entry_bar = self._entry_bar.get(key)
        if min_hold > 0 and entry_bar is not None and bar - entry_bar < min_hold:
            return False  # 최소 보유 기간 미달
        return True

    def _entry_blocked(self, conn: sqlite3.Connection) -> bool:
        """신규 매수 차단 여부 — 하루 손실 한도 초과 또는 진입 금지 시간대."""
        from datetime import datetime, timedelta, timezone

        limits = risk_limit_service.get_limits(conn, self._settings, self._mode)
        mdl = int(limits.get("max_daily_loss", 0) or 0)
        if mdl > 0 and risk_limit_service.today_realized_pnl(conn, self._mode) <= -mdl:
            return True  # 하루 손실 한도 초과
        now = datetime.now(timezone(timedelta(hours=9)))
        return in_entry_block_window(
            now,
            int(self._settings.entry_block_after_open_min),
            int(self._settings.entry_block_before_close_min),
        )

    async def _check_stops(
        self,
        conn: sqlite3.Connection,
        key: tuple[str, str],
        symbol: str,
        price: float,
        hist: list[float],
        cfg: dict[str, Any],
    ) -> bool:
        """보유 중 보호 청산(손절/익절/트레일링)을 검사·집행한다. 청산했으면 True.

        거버너(최소보유/쿨다운)를 무시하고 즉시 매도한다(보호 목적).
        """
        entry = self._entry_price.get(key)
        if entry is None:
            return False
        if bot_sellable_qty(conn, symbol, self._mode) <= 0:
            # 더 이상 봇 보유가 없으면 상태 정리
            self._entry_price.pop(key, None)
            self._high_price.pop(key, None)
            return False
        high = max(self._high_price.get(key, entry), price)
        self._high_price[key] = high
        reason = stop_exit_reason(entry, high, price, cfg.get("params", {}))
        if reason is None:
            return False

        sig = Signal(symbol=symbol, strategy=cfg["strategy"], side="SELL", price=price, reason=reason)
        placed = await self._handle_signal(conn, sig, cfg)
        if placed == "SELL":
            self._last_signal_side[key] = "SELL"
            self._exit_bar[key] = self._bar_index(hist, cfg)
            self._entry_bar.pop(key, None)
            self._entry_price.pop(key, None)
            self._high_price.pop(key, None)
            return True
        return False

    async def _handle_signal(
        self, conn: sqlite3.Connection, signal: Any, cfg: dict[str, Any]
    ) -> str | None:
        """신호를 주문으로 집행한다. 실제로 주문이 전송(성공)되면 side를 반환, 아니면 None."""
        # 미보유 매도 억제: 봇이 팔 수량이 없으면(매도가능 0) 신호를 주문으로 만들지 않는다.
        # 가드(NO_BOT_HOLDING)가 어차피 거부하지만, 거절 주문/신호 폭증을 신호 단계에서 막는다.
        if signal.side == "SELL" and bot_sellable_qty(conn, signal.symbol, self._mode) <= 0:
            logger.debug("매도 신호 무시(매도가능 0): %s %s", self._mode, signal.symbol)
            return None

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
            return None

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
            return signal.side  # 실제 전송 성공 → 거버너 진입/청산 봉 기록용
        return None

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
