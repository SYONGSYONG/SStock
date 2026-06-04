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
    risk_limit_service,
    signal_service,
    strategy_service,
)


def _setup(tmp_path, **settings_kw):
    path = str(tmp_path / "test.db")
    init_db(path)
    conn = connect(path)
    strategy_service.upsert_config(
        conn, "005930", "ma_cross", {"short": 2, "long": 4, "bar_ticks": 1}, enabled=True
    )
    # 봇이 매매하려면 칸막이 등록이 필수 → 충분한 원금을 배정
    budget_service.set_principal(conn, "005930", 10_000_000)
    conn.close()

    params = dict(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
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


def test_거버너_쿨다운_최소보유(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)
    key = ("005930", "ma_cross")
    cfg_cd = {"params": {"bar_ticks": 1, "cooldown_bars": 5}}
    cfg_mh = {"params": {"bar_ticks": 1, "min_hold_bars": 5}}

    # 쿨다운: 매도 후 5봉 이내 매수 금지
    bot._exit_bar[key] = 10
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 12, cfg_cd) is False  # 12-10<5
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 16, cfg_cd) is True  # 16-10>=5

    # 최소보유: 매수 후 5봉 이내 매도 금지
    bot._entry_bar[key] = 10
    assert bot._governor_allows(conn, key, "SELL", [0.0] * 12, cfg_mh) is False
    assert bot._governor_allows(conn, key, "SELL", [0.0] * 16, cfg_mh) is True
    conn.close()


def test_거버너_미체결매수_중복방지(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)
    key = ("005930", "ma_cross")
    cfg = {"params": {"bar_ticks": 1}}
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 5, cfg) is True
    # 미체결 매수가 있으면 신규 매수 차단
    order_service.save_order(conn, "005930", "BUY", 1, 1000, "paper", status="requested")
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 5, cfg) is False
    conn.close()


def test_거버너_하루손실_한도_매수차단(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)
    key = ("005930", "ma_cross")
    cfg = {"params": {"bar_ticks": 1}}
    # 당일 손실 실현: 10@1000 매수 → 10@900 매도(실현 약 -1000)
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    order_service.save_order(conn, "005930", "SELL", 10, 900, "paper", status="filled")
    # 한도 off → 매수 허용
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 5, cfg) is True
    # 하루 손실 한도 500 → 손실 초과 → 매수 차단
    risk_limit_service.set_limits(conn, "paper", 100, 1_000_000, 500)
    assert bot._governor_allows(conn, key, "BUY", [0.0] * 5, cfg) is False
    conn.close()


async def test_손절_보호청산(tmp_path):
    path, settings = _setup(tmp_path)
    calls: list[str] = []

    async def placer(symbol, side, qty, price):
        calls.append(side)
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    async def syncer(symbol, order_no):
        return []

    bot = TradingBot(
        conn_factory=lambda: connect(path),
        settings=settings,
        order_placer=placer,
        order_syncer=syncer,
    )
    conn = connect(path)
    budget_service.set_principal(conn, "005930", 10_000_000)
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    key = ("005930", "ma_cross")
    bot._entry_price[key] = 1000.0
    bot._high_price[key] = 1000.0
    # 손절 5틱(tick=1) → 손절선 995. 현재가 990 → 보호 청산
    cfg = {"strategy": "ma_cross", "params": {"bar_ticks": 1, "stop_loss_ticks": 5}}
    handled = await bot._check_stops(conn, key, "005930", 990.0, [0.0] * 5, cfg)
    assert handled is True
    assert calls == ["SELL"]
    assert key not in bot._entry_price  # 청산 후 상태 정리
    conn.close()


async def test_같은방향_중복신호_억제(tmp_path):
    # 확정봉이 그대로인 채 미완성 틱만 추가되면 같은 BUY 신호가 다시 떠도,
    # 봇은 직전과 같은 방향 신호를 억제해 주문을 1건만 낸다(휘프소 폭증 방지).
    path = str(tmp_path / "t.db")
    init_db(path)
    conn = connect(path)
    strategy_service.upsert_config(
        conn, "005930", "ma_cross", {"short": 2, "long": 4, "bar_ticks": 2}, enabled=True
    )
    budget_service.set_principal(conn, "005930", 10_000_000)
    conn.close()
    settings = Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        daily_max_orders=100,
        daily_max_amount=10_000_000,
    )
    calls: list[str] = []

    async def placer(symbol, side, qty, price):
        calls.append(side)
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    async def syncer(symbol, order_no):
        return []  # 체결 동기화는 빈 응답(실 KIS 호출 방지)

    bot = TradingBot(
        conn_factory=lambda: connect(path),
        settings=settings,
        order_placer=placer,
        order_syncer=syncer,
    )
    await bot.start()
    # 12틱(각 봉 2틱) → 확정봉 [10,9,8,7,6,20]에서 골든크로스 BUY 1회
    await _feed(bot, [10, 10, 9, 9, 8, 8, 7, 7, 6, 6, 20, 20])
    # 미완성 틱 1개 추가 → 확정봉 동일 → 같은 BUY 재발생하지만 억제됨
    await bot.on_tick({"symbol": "005930", "price": 20})

    assert calls == ["BUY"]  # 중복 BUY 없이 1건만
    await bot.stop()


async def test_미보유_매도신호는_주문생성_안함(tmp_path):
    # BUY가 거절되어 봇 보유가 0인 상태에서 데드크로스(SELL)가 떠도,
    # 매도가능 0이면 봇은 신호를 주문으로 만들지 않는다(거절 주문조차 남기지 않음).
    path, settings = _setup(tmp_path, daily_max_amount=10)  # BUY(20원) 거절 유도
    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    await bot.start()
    # 틱6에서 BUY(금액 한도 거절) → 틱9에서 SELL(미보유 → 억제)
    await _feed(bot, [10, 9, 8, 7, 6, 20, 18, 12, 8, 6, 5, 5])

    # 매도 주문은 시도조차 하지 않음
    assert all(c[1] != "SELL" for c in calls)
    conn = connect(path)
    # 가드 거절(BUY)은 주문에 안 남고, 미보유 매도(SELL)는 억제 → orders 비어 있음
    assert order_service.list_orders(conn) == []
    # 거절 사유는 감사 로그(RISK)에만 남는다
    assert any(
        log["category"] == "RISK" and "BUY" in log["message"]
        for log in audit_service.list_logs(conn)
    )
    conn.close()
    await bot.stop()


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
    # 가드 거절은 KIS로 전송되지 않으므로 주문 내역에 남기지 않는다(감사 로그에만 기록)
    assert order_service.list_orders(conn) == []
    assert any(log["category"] == "RISK" for log in audit_service.list_logs(conn))
    conn.close()
    await bot.stop()
