"""자동매매 봇 테스트."""

from __future__ import annotations

from app.bot.trading_bot import TradingBot
from app.config import Settings
from app.db.database import connect, init_db
from app.kis.orders import OrderResult
from app.services import (
    audit_service,
    budget_service,
    order_service,
    signal_service,
    strategy_service,
)


def _setup(tmp_path, **settings_kw):
    path = str(tmp_path / "test.db")
    init_db(path)
    conn = connect(path)
    strategy_service.upsert_config(conn, "005930", "ma_cross", {"short": 2, "long": 4}, enabled=True)
    # 봇이 매매하려면 칸막이 등록이 필수 → 충분한 원금을 배정
    budget_service.set_principal(conn, "005930", 10_000_000)
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


async def test_신호_주문_생성_및_체결동기화(tmp_path):
    path, settings = _setup(tmp_path)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X1", message="ok")

    async def fake_syncer(symbol, order_no):
        return [
            {
                "odno": order_no,
                "ord_qty": 1,
                "tot_ccld_qty": 1,
                "rmn_qty": 0,
                "cncl_yn": "N",
                "rjct_qty": 0,
            }
        ]

    bot = TradingBot(
        conn_factory=lambda: connect(path),
        settings=settings,
        order_placer=fake_placer,
        order_syncer=fake_syncer,
    )
    await bot.start()
    await _feed(bot, [10, 9, 8, 7, 6, 20])
    await bot.sync_orders(force=True)

    assert len(calls) == 1
    assert calls[0][1] == "BUY"

    conn = connect(path)
    assert signal_service.list_signals(conn)[0]["side"] == "BUY"
    orders = order_service.list_orders(conn)
    assert orders[0]["status"] == "filled"
    assert orders[0]["filled_qty"] == 1
    assert orders[0]["remaining_qty"] == 0
    assert any(log["category"] == "ORDER" for log in audit_service.list_logs(conn))
    conn.close()
    await bot.stop()


async def test_봇_OFF면_주문없음(tmp_path):
    path, settings = _setup(tmp_path)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    await _feed(bot, [10, 9, 8, 7, 6, 20])

    assert calls == []
    conn = connect(path)
    assert order_service.list_orders(conn) == []
    conn.close()


async def test_가용_한도_초과면_거절(tmp_path):
    path, settings = _setup(tmp_path, daily_max_amount=10)
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    await bot.start()
    await _feed(bot, [10, 9, 8, 7, 6, 20])

    assert calls == []
    conn = connect(path)
    orders = order_service.list_orders(conn)
    assert orders[0]["status"] == "rejected"
    assert any(log["category"] == "RISK" for log in audit_service.list_logs(conn))
    conn.close()
    await bot.stop()
