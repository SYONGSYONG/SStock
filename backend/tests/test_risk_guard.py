"""주문 안전 가드 테스트."""

from __future__ import annotations

import sqlite3

import pytest

from app.config import Settings
from app.db.database import connect, init_db
from app.services import budget_service, order_service
from app.services.risk_guard import OrderIntent, RiskError, check_order


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def _envelope(conn: sqlite3.Connection, symbol: str = "005930", principal: int = 10**9) -> None:
    """일일 한도 등을 테스트하려면 먼저 칸막이를 등록해야 매매 가드를 통과한다."""
    budget_service.set_principal(conn, symbol, principal)


def _settings(**kw) -> Settings:
    base = dict(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        daily_max_orders=5,
        daily_max_amount=1_000_000,
    )
    base.update(kw)
    return Settings(**base)


def test_정상_주문은_통과(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    check_order(conn, _settings(), OrderIntent("005930", "BUY", 1, 70000))  # 예외 없음


def test_종목_수량_한도_초과(tmp_path):
    conn = _db(tmp_path)
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 10, 70000, max_qty=5))
    assert e.value.code == "SYMBOL_QTY_LIMIT"


def test_종목_금액_한도_초과(tmp_path):
    conn = _db(tmp_path)
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "BUY", 2, 70000, max_amount=100000))
    assert e.value.code == "SYMBOL_AMOUNT_LIMIT"


def test_일일_주문_횟수_한도(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    s = _settings(daily_max_orders=2)
    for _ in range(2):
        order_service.save_order(conn, "005930", "BUY", 1, 100, "paper", status="requested")
    with pytest.raises(RiskError) as e:
        check_order(conn, s, OrderIntent("005930", "BUY", 1, 100))
    assert e.value.code == "DAILY_ORDER_LIMIT"


def test_일일_주문_금액_한도(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    s = _settings(daily_max_amount=500000)
    order_service.save_order(conn, "005930", "BUY", 4, 100000, "paper", status="requested")
    with pytest.raises(RiskError) as e:
        check_order(conn, s, OrderIntent("005930", "BUY", 2, 100000))  # 누적 60만 > 50만
    assert e.value.code == "DAILY_AMOUNT_LIMIT"


def test_거부된_주문은_한도에_미포함(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    s = _settings(daily_max_orders=1)
    order_service.save_order(conn, "005930", "BUY", 1, 100, "paper", status="rejected")
    # 거부 주문은 카운트 제외 → 통과
    check_order(conn, s, OrderIntent("005930", "BUY", 1, 100))


def test_칸막이_미등록_종목은_매수_금지(tmp_path):
    conn = _db(tmp_path)
    # 칸막이 미등록 → 매수 금지
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("000660", "BUY", 1, 1000))
    assert e.value.code == "ENVELOPE_REQUIRED"


def test_칸막이_미등록_종목은_매도_금지(tmp_path):
    conn = _db(tmp_path)
    # 칸막이 미등록 → 매도 금지(기보유분 보호의 1차 방어선)
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("000660", "SELL", 1, 1000))
    assert e.value.code == "ENVELOPE_REQUIRED"


def test_봇_보유없는_종목_매도_차단(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)  # 칸막이는 있으나 봇이 산 적 없음
    # 실제 계좌에 기보유분이 있어도 봇 주문 이력상 보유 0 → 매도 차단
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "SELL", 1, 1000))
    assert e.value.code == "SELL_EXCEEDS_HOLDING"


def test_봇_보유수량_초과_매도_차단(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    # 봇이 5주 매수 체결 → 6주 매도는 차단
    order_service.save_order(conn, "005930", "BUY", 5, 1000, "paper", status="filled")
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "SELL", 6, 1000))
    assert e.value.code == "SELL_EXCEEDS_HOLDING"


def test_봇_보유수량_이내_매도_통과(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    # 봇이 5주 매수 체결 → 5주 매도는 통과
    order_service.save_order(conn, "005930", "BUY", 5, 1000, "paper", status="filled")
    check_order(conn, _settings(), OrderIntent("005930", "SELL", 5, 1000))  # 예외 없음


def test_미체결_매도_중복_차단(tmp_path):
    conn = _db(tmp_path)
    _envelope(conn)
    order_service.save_order(conn, "005930", "BUY", 5, 1000, "paper", status="filled")
    # 이미 3주 매도 미체결(remaining 3) → 남은 매도 가능분은 2주
    order_service.save_order(conn, "005930", "SELL", 3, 1000, "paper", status="requested")
    check_order(conn, _settings(), OrderIntent("005930", "SELL", 2, 1000))  # 2주는 통과
    with pytest.raises(RiskError) as e:
        check_order(conn, _settings(), OrderIntent("005930", "SELL", 3, 1000))  # 3주는 초과
    assert e.value.code == "SELL_EXCEEDS_HOLDING"
