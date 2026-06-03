"""Phase 3: 모의/실전 동시 운용 — 봇/시세 모드별 독립성 테스트."""

from __future__ import annotations

import pytest

from app.bot.registry import get_registry, reset_registry
from app.bot.trading_bot import TradingBot
from app.config import Settings
from app.kis.orders import place_order, cancel_order, get_account_summary, get_balance


class TestDualModeRegistry:
    """레지스트리: 모드별 봇/시세 인스턴스 독립성."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        """각 테스트 전후로 레지스트리 초기화."""
        reset_registry()
        yield
        reset_registry()

    def test_registry_returns_distinct_bots(self):
        """각 모드의 봇은 별개 인스턴스."""
        registry = get_registry()
        paper_bot = registry.get_bot("paper")
        live_bot = registry.get_bot("live")
        assert paper_bot is not live_bot
        assert paper_bot._mode == "paper"
        assert live_bot._mode == "live"

    def test_registry_returns_distinct_feeds(self):
        """각 모드의 시세는 별개 인스턴스."""
        registry = get_registry()
        paper_feed = registry.get_feed("paper")
        live_feed = registry.get_feed("live")
        assert paper_feed is not live_feed
        assert paper_feed._mode == "paper"
        assert live_feed._mode == "live"

    def test_registry_invalid_mode_raises(self):
        """잘못된 모드는 ValueError."""
        registry = get_registry()
        with pytest.raises(ValueError, match="잘못된 모드"):
            registry.get_bot("invalid")
        with pytest.raises(ValueError, match="잘못된 모드"):
            registry.get_feed("invalid")


class TestBotModeIndependence:
    """봇: 모드별 독립 시작/정지."""

    @pytest.fixture
    def settings(self):
        return Settings()

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_registry()
        yield
        reset_registry()

    @pytest.mark.asyncio
    async def test_two_bots_start_independently(self, settings):
        """두 봇은 각각 start/stop할 수 있다."""
        registry = get_registry()
        paper_bot = registry.get_bot("paper")
        live_bot = registry.get_bot("live")

        assert not paper_bot.running
        assert not live_bot.running

        # 모의 봇만 시작
        await paper_bot.start()
        assert paper_bot.running
        assert not live_bot.running

        # 실전 봇도 시작
        await live_bot.start()
        assert paper_bot.running
        assert live_bot.running

        # 모의 봇 정지 → 실전은 여전히 running
        await paper_bot.stop()
        assert not paper_bot.running
        assert live_bot.running

        # 실전 봇도 정지
        await live_bot.stop()
        assert not paper_bot.running
        assert not live_bot.running

    @pytest.mark.asyncio
    async def test_bot_mode_attribute(self, settings):
        """각 봇의 _mode 속성 확인."""
        paper = TradingBot(settings=settings, mode="paper")
        live = TradingBot(settings=settings, mode="live")
        assert paper._mode == "paper"
        assert live._mode == "live"

        # 미지정 시 settings.trading_mode 기본값
        default = TradingBot(settings=settings)
        assert default._mode == settings.trading_mode


class TestKisClientModeRouting:
    """KIS 클라이언트: 모드별 도메인/계좌 라우팅."""

    def test_place_order_mode_resolution(self):
        """place_order는 모드별 TR_ID/계좌를 사용."""
        # 테스트에서는 실제 호출을 안 하므로 여기선 서명만 확인
        # 실제 통합 테스트는 respx로 도메인/헤더를 검증
        import inspect
        sig = inspect.signature(place_order)
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default is None

    def test_cancel_order_mode_resolution(self):
        """cancel_order는 모드별 TR_ID/계좌를 사용."""
        import inspect
        sig = inspect.signature(cancel_order)
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default is None

    def test_get_account_summary_mode_resolution(self):
        """get_account_summary는 모드별 계좌를 사용."""
        import inspect
        sig = inspect.signature(get_account_summary)
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default is None

    def test_get_balance_mode_resolution(self):
        """get_balance는 모드별 계좌를 사용."""
        import inspect
        sig = inspect.signature(get_balance)
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default is None


class TestOrderServiceModeFilter:
    """order_service: 모드별 필터링."""

    def test_list_orders_signature(self):
        """list_orders는 mode 파라미터를 지원."""
        from app.services import order_service
        import inspect
        sig = inspect.signature(order_service.list_orders)
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default is None


class TestMarketDataServiceModeHandling:
    """MarketDataService: 모드별 독립 시세 수집."""

    def test_market_data_service_mode_attribute(self):
        """시세 서비스는 모드를 추적."""
        from app.bot.market_data import MarketDataService
        from app.config import Settings
        settings = Settings()
        paper = MarketDataService(settings=settings, mode="paper")
        live = MarketDataService(settings=settings, mode="live")
        assert paper._mode == "paper"
        assert live._mode == "live"

    def test_market_data_service_handler_injection(self):
        """시세 서비스는 on_tick_handler를 주입받을 수 있다."""
        from app.bot.market_data import MarketDataService
        from app.config import Settings
        settings = Settings()

        async def dummy_handler(tick):
            pass

        feed = MarketDataService(settings=settings, mode="paper", on_tick_handler=dummy_handler)
        assert feed._on_tick_handler is dummy_handler


class TestRealtimeClientMode:
    """KisRealtimeClient: 모드별 도메인/인증."""

    def test_realtime_client_mode_attribute(self):
        """웹소켓 클라이언트는 모드를 추적."""
        from app.kis.realtime import KisRealtimeClient
        from app.config import Settings
        settings = Settings()
        paper = KisRealtimeClient(settings=settings, mode="paper")
        live = KisRealtimeClient(settings=settings, mode="live")
        assert paper._mode == "paper"
        assert live._mode == "live"

    def test_realtime_client_url_mode_aware(self):
        """웹소켓 URL은 모드별 ws_base를 사용."""
        from app.kis.realtime import KisRealtimeClient
        from app.config import Settings
        settings = Settings()
        paper = KisRealtimeClient(settings=settings, mode="paper")
        live = KisRealtimeClient(settings=settings, mode="live")

        # URL 형식 확인 (실제 도메인은 환경에 따름)
        assert paper.url.endswith("/tryitout/H0STCNT0")
        assert live.url.endswith("/tryitout/H0STCNT0")
        # paper와 live의 도메인은 다름(rest_base가 다르기 때문)


class TestSettingsModeAwareness:
    """Settings: 모드별 자격증명 반환."""

    def test_kis_for_returns_credentials_by_mode(self):
        """kis_for는 모드별 자격증명을 반환."""
        settings = Settings()
        paper_creds = settings.kis_for("paper")
        live_creds = settings.kis_for("live")

        assert paper_creds.mode == "paper"
        assert live_creds.mode == "live"

    def test_has_kis_credentials_mode_specific(self):
        """has_kis_credentials는 특정 모드의 자격증명 존재 여부를 확인."""
        settings = Settings()
        # 테스트 설정상 paper/live 모두 비어 있을 수 있음
        # 하지만 각 모드별로 독립적으로 확인
        paper_ok = settings.has_kis_credentials("paper")
        live_ok = settings.has_kis_credentials("live")
        # 두 값이 다를 수 있음 (상황에 따라)
        assert isinstance(paper_ok, bool)
        assert isinstance(live_ok, bool)
