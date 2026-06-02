"""자동매매 봇 파이프라인 테스트 (시세→전략→신호→가드→주문)."""

from __future__ import annotations

from app.bot.trading_bot import TradingBot
from app.config import Settings
from app.db.database import connect, init_db
from app.kis.orders import OrderResult
from app.services import audit_service, order_service, signal_service, strategy_service


def _setup(tmp_path, **settings_kw):
    path = str(tmp_path / "test.db")
    init_db(path)
    conn = connect(path)
    strategy_service.upsert_config(conn, "005930", "ma_cross", {"short": 2, "long": 4}, enabled=True)
    conn.close()

    params = dict(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        daily_max_orders=10,
        daily_max_amount=10_000_000,
    )
    params.update(settings_kw)
    settings = Settings(**params)
    return path, settings


async def _feed(bot: TradingBot, prices: list[float]) -> None:
    for p in prices:
        await bot.on_tick({"symbol": "005930", "price": p})


async def test_골든크로스시_모의주문_집행(tmp_path):
    path, settings = _setup(tmp_path)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X1", message="ok")

    bot = TradingBot(
        conn_factory=lambda: connect(path),
        settings=settings,
        order_placer=fake_placer,
    )
    await bot.start()
    await _feed(bot, [10, 9, 8, 7, 6, 20])  # 마지막에 골든크로스

    assert len(calls) == 1
    assert calls[0][1] == "BUY"

    conn = connect(path)
    assert signal_service.list_signals(conn)[0]["side"] == "BUY"
    orders = order_service.list_orders(conn)
    assert orders[0]["status"] == "requested"
    assert orders[0]["kis_order_no"] == "X1"
    assert any(log["category"] == "ORDER" for log in audit_service.list_logs(conn))
    conn.close()


async def test_봇_OFF면_주문없음(tmp_path):
    path, settings = _setup(tmp_path)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    # start() 호출 안 함 → 기본 OFF
    await _feed(bot, [10, 9, 8, 7, 6, 20])

    assert calls == []
    conn = connect(path)
    assert order_service.list_orders(conn) == []
    conn.close()


async def test_가드_위반시_주문거부_집행안함(tmp_path):
    # 일일 금액 한도를 매우 작게 → 주문 거부
    path, settings = _setup(tmp_path, daily_max_amount=10)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    await bot.start()
    await _feed(bot, [10, 9, 8, 7, 6, 20])

    assert calls == []  # 집행기 호출 안 됨
    conn = connect(path)
    orders = order_service.list_orders(conn)
    assert orders[0]["status"] == "rejected"
    assert any(log["category"] == "RISK" for log in audit_service.list_logs(conn))
    conn.close()
