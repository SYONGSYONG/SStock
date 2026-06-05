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


async def test_OFF전략_관찰신호만_기록(tmp_path):
    """봇이 켜져 있어도 전략이 OFF면 신호를 '관찰 전용'으로만 기록하고 주문은 내지 않는다."""
    path, settings = _setup(tmp_path)
    # _setup이 등록한 enabled 전략을 OFF로 전환
    conn = connect(path)
    cfg = strategy_service.list_configs(conn, mode="paper")[0]
    strategy_service.set_enabled(conn, cfg["id"], False)
    conn.close()

    calls: list[tuple] = []

    async def fake_placer(symbol, side, qty, price):
        calls.append((symbol, side, qty, price))
        return OrderResult(ok=True, kis_order_no="X", message="ok")

    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings, order_placer=fake_placer)
    await bot.start()
    await _feed(bot, [10, 9, 8, 7, 6, 20])
    await bot.stop()

    # 실주문은 전혀 나가지 않는다
    assert calls == []
    conn = connect(path)
    assert order_service.list_orders(conn) == []
    # 관찰 신호(observe=1)는 기록된다
    sigs = signal_service.list_signals(conn)
    assert len(sigs) >= 1
    assert sigs[0]["side"] == "BUY"
    assert sigs[0]["observe"] == 1
    conn.close()


def test_그림자_국면_히스테리시스(tmp_path, monkeypatch):
    """국면은 REGIME_CONFIRM개 봉 연속 확정될 때만 전환 로그를 남긴다(플래핑은 무시)."""
    from app.bot import trading_bot as tb

    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)

    # 매 호출=1봉, 확정 3회로 단순화
    monkeypatch.setattr(tb, "regime_bar_ticks", lambda params=None: 1)
    monkeypatch.setattr(tb, "REGIME_CONFIRM", 3)

    seq = iter(
        [
            "강한하강", "횡보노이즈", "강한하강",  # 플래핑 → 확정 안 됨(로그 없음)
            "강한상승", "강한상승", "강한상승",  # 3연속 → 최초 감지 로그
            "강한하강", "강한하강", "강한하강",  # 3연속 → 전환 로그
        ]
    )
    monkeypatch.setattr(tb, "classify_regime", lambda hist: next(seq))

    for _ in range(9):
        bot._shadow_regime(conn, "005930", [0.0])

    logs = [g for g in audit_service.list_logs(conn) if g["category"] == "REGIME"]
    assert len(logs) == 2  # 플래핑 3건 무시 + 감지 1 + 전환 1
    assert "전환" in logs[0]["message"]  # 최신(DESC)이 전환
    assert "감지" in logs[1]["message"] and "강한상승" in logs[1]["message"]
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


def test_거버너_변동성_거래대금_필터(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)
    key = ("005930", "ma_cross")
    cfg = {"params": {"bar_ticks": 1, "min_volatility_ticks": 2}}
    # 조용한 구간(범위 0) → 변동성 부족으로 매수 차단
    assert bot._governor_allows(conn, key, "BUY", [10000.0] * 25, cfg) is False
    # 충분한 변동(범위 500=5틱) → 허용
    hist = [10000.0] * 24 + [10500.0]
    assert bot._governor_allows(conn, key, "BUY", hist, cfg) is True

    # 거래대금 필터: 거래량 변화 없음 → 차단
    cfg2 = {"params": {"bar_ticks": 1, "min_turnover": 1_000_000}}
    bot._vol_history["005930"] = [100.0, 100.0, 100.0]
    assert bot._governor_allows(conn, key, "BUY", [10000.0] * 5, cfg2) is False
    # 거래대금 충분 → 허용
    bot._vol_history["005930"] = [100.0, 1_000_000.0]
    assert bot._governor_allows(conn, key, "BUY", [10000.0] * 5, cfg2) is True
    conn.close()


def test_거버너_스프레드_필터(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    conn = connect(path)
    key = ("005930", "ma_cross")
    cfg = {"params": {"bar_ticks": 1, "max_spread_ticks": 3}}  # tick(10000)=10 → 한도 30원
    hist = [10000.0] * 5
    # 스프레드 미수신 → 통과
    assert bot._governor_allows(conn, key, "BUY", hist, cfg) is True
    bot._spread["005930"] = 50  # 50 > 30 → 차단
    assert bot._governor_allows(conn, key, "BUY", hist, cfg) is False
    bot._spread["005930"] = 20  # 20 <= 30 → 통과
    assert bot._governor_allows(conn, key, "BUY", hist, cfg) is True
    conn.close()


async def test_호가틱_스프레드_갱신(tmp_path):
    path, settings = _setup(tmp_path)
    bot = TradingBot(conn_factory=lambda: connect(path), settings=settings)
    bot._running = True
    await bot.on_tick({"kind": "orderbook", "symbol": "005930", "ask": 70100, "bid": 70000})
    assert bot._spread["005930"] == 100


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


async def test_손절_보호청산_재시작후_진입가복원(tmp_path):
    """재시작으로 메모리 진입가가 없어도 봇 보유원가에서 복원해 손절이 동작한다."""
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
    # 봇이 1,000원에 10주 보유(주문 이력). 메모리 진입가 상태는 '없음'(재시작 가정).
    order_service.save_order(conn, "005930", "BUY", 10, 1000, "paper", status="filled")
    key = ("005930", "rsi_ma")
    assert key not in bot._entry_price  # 진입가 상태 없음
    # 손절 5틱(tick=1) → 손절선 995. 현재가 990 → 보유원가(1,000)에서 복원해 손절
    cfg = {"strategy": "rsi_ma", "params": {"bar_ticks": 1, "stop_loss_ticks": 5}}
    handled = await bot._check_stops(conn, key, "005930", 990.0, [0.0] * 5, cfg)
    assert handled is True
    assert calls == ["SELL"]
    conn.close()


async def test_주문가_호가단위_정렬(tmp_path):
    """봇이 주문가를 호가단위 배수로 정렬해 전송한다('호가단위 오류' 거절 방지)."""
    from app.strategies.base import Signal

    path, settings = _setup(tmp_path)
    prices: list[float] = []

    async def placer(symbol, side, qty, price):
        prices.append(price)
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
    budget_service.set_principal(conn, "005930", 100_000_000)
    # 신호가 330,750(호가단위 500 비배수) → 331,000으로 정렬해 주문
    sig = Signal(symbol="005930", strategy="rsi_ma", side="BUY", price=330750.0, reason="t")
    await bot._handle_signal(conn, sig, {"params": {}, "max_qty": 1})
    assert prices == [331000.0]
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
