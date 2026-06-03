"""실시간 시세 수집 서비스."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import Settings, get_settings
from app.kis.realtime import KisRealtimeClient
from app.realtime.hub import hub

logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: KisRealtimeClient | None = None
        self._task: asyncio.Task[None] | None = None
        self._symbols: list[str] = []

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
        self._client = KisRealtimeClient(self._settings)
        self._task = asyncio.create_task(self._client.run(self._symbols, self._on_tick))
        logger.info("MarketDataService 시작: %s", self._symbols)

    async def refresh(self, symbols: list[str]) -> None:
        """현재 관심종목 목록으로 실시간 구독을 다시 맞춘다."""
        if self.running:
            await self.stop()
            await self.start(symbols)
        else:
            self._symbols = list(symbols)

    async def _on_tick(self, tick: dict[str, Any]) -> None:
        await hub.broadcast({"type": "tick", "data": tick})
        from app.bot.trading_bot import trading_bot

        await trading_bot.on_tick(tick)

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
        logger.info("MarketDataService 정지")


market_data_service = MarketDataService()
