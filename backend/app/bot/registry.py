"""모드별(paper/live) 자동매매 봇과 실시간 시세 서비스 레지스트리.

두 봇과 시세 서비스는 각자 on/off로 독립 동작한다.
각 모드의 시세 서비스는 해당 모드 봇으로 tick을 라우팅한다.
"""

from __future__ import annotations

from typing import Any

from app.bot.market_data import MarketDataService
from app.bot.trading_bot import TradingBot
from app.config import Settings, get_settings

MODES = ("paper", "live")


class BotRegistry:
    """모드별 자동매매 봇과 실시간 시세 서비스 레지스트리."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._bots: dict[str, TradingBot] = {}
        self._feeds: dict[str, MarketDataService] = {}

        # 모드별 초기화: 각 모드별 봇 + 시세
        for mode in MODES:
            bot = TradingBot(settings=self._settings, default_qty=1, mode=mode)
            self._bots[mode] = bot

            # 시세 서비스: 이 모드 봇의 on_tick을 핸들러로 주입
            # 시세가 tick을 받으면 해당 모드 봇의 on_tick으로 전달
            feed = MarketDataService(settings=self._settings, mode=mode, on_tick_handler=bot.on_tick)
            self._feeds[mode] = feed

    def get_bot(self, mode: str) -> TradingBot:
        """모드별 봇을 반환한다."""
        if mode not in MODES:
            raise ValueError(f"잘못된 모드: {mode}. 허용값: {list(MODES)}")
        return self._bots[mode]

    def get_feed(self, mode: str) -> MarketDataService:
        """모드별 시세 서비스를 반환한다."""
        if mode not in MODES:
            raise ValueError(f"잘못된 모드: {mode}. 허용값: {list(MODES)}")
        return self._feeds[mode]

    def bots(self) -> dict[str, TradingBot]:
        """모든 봇을 반환한다."""
        return self._bots

    def feeds(self) -> dict[str, MarketDataService]:
        """모든 시세 서비스를 반환한다."""
        return self._feeds


# 전역 레지스트리 인스턴스
_registry: BotRegistry | None = None


def get_registry() -> BotRegistry:
    """전역 봇 레지스트리를 반환한다(lazy 초기화)."""
    global _registry
    if _registry is None:
        _registry = BotRegistry()
    return _registry


def reset_registry() -> None:
    """테스트용: 전역 레지스트리를 초기화한다."""
    global _registry
    _registry = None
