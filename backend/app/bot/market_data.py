"""실시간 시세 수집 서비스."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Settings, get_settings
from app.kis.realtime import KisRealtimeClient
from app.realtime.hub import hub

logger = logging.getLogger(__name__)

TickHandler = Callable[[dict[str, Any]], Awaitable[None]]


class MarketDataService:
    """모드별 실시간 시세 수집 서비스.

    mode: 모드별 tick을 수집. 미지정 시 settings.trading_mode.
    on_tick_handler: tick 수신 시 호출할 핸들러(예: 해당 모드 봇의 on_tick).
                     미지정 시 hub.broadcast만 실행.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        mode: str | None = None,
        on_tick_handler: TickHandler | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._mode = mode or self._settings.trading_mode
        self._client: KisRealtimeClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._symbols: list[str] = []
        self._on_tick_handler = on_tick_handler

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)

    async def start(self, symbols: list[str]) -> None:
        if self.running:
            return
        self._symbols = list(symbols)
        self._client = KisRealtimeClient(self._settings, mode=self._mode)
        self._task = asyncio.create_task(self._client.run(self._symbols, self._on_tick))
        logger.info("MarketDataService[%s] 시작: %s", self._mode, self._symbols)

    async def refresh(self, symbols: list[str]) -> None:
        """현재 관심종목 목록으로 실시간 구독을 다시 맞춘다."""
        if self.running:
            await self.stop()
            await self.start(symbols)
        else:
            self._symbols = list(symbols)

    async def _on_tick(self, tick: dict[str, Any]) -> None:
        """tick을 수신해 broadcast와 핸들러로 전달한다.

        호가(orderbook) 메시지는 대시보드에 불필요하므로 브로드캐스트하지 않고 봇 핸들러로만
        전달한다(스프레드 갱신용).
        """
        if tick.get("kind") == "orderbook":
            if self._on_tick_handler is not None:
                await self._on_tick_handler(tick)
            return

        # broadcast에 mode 태그 추가
        await hub.broadcast({"type": "tick", "mode": self._mode, "data": tick})

        # 주입된 핸들러가 있으면 호출(해당 모드 봇)
        if self._on_tick_handler is not None:
            await self._on_tick_handler(tick)

    async def stop(self) -> None:
        if self._client is not None:
            self._client.stop()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._task = None
        self._client = None
        logger.info("MarketDataService[%s] 정지", self._mode)
