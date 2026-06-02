"""주문 안전 가드 테스트."""

from __future__ import annotations

import sqlite3

import pytest

from app.config import Settings
from app.db.database import connect, init_db
from app.services import order_service
from app.services.risk_guard import OrderIntent, RiskError, check_order


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


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
    s = _settings(daily_max_orders=2)
    for _ in range(2):
        order_service.save_order(conn, "005930", "BUY", 1, 100, "paper", status="requested")
    with pytest.raises(RiskError) as e:
        check_order(conn, s, OrderIntent("005930", "BUY", 1, 100))
    assert e.value.code == "DAILY_ORDER_LIMIT"


def test_일일_주문_금액_한도(tmp_path):
    conn = _db(tmp_path)
    s = _settings(daily_max_amount=500000)
    order_service.save_order(conn, "005930", "BUY", 4, 100000, "paper", status="requested")
    with pytest.raises(RiskError) as e:
        check_order(conn, s, OrderIntent("005930", "BUY", 2, 100000))  # 누적 60만 > 50만
    assert e.value.code == "DAILY_AMOUNT_LIMIT"


def test_거부된_주문은_한도에_미포함(tmp_path):
    conn = _db(tmp_path)
    s = _settings(daily_max_orders=1)
    order_service.save_order(conn, "005930", "BUY", 1, 100, "paper", status="rejected")
    # 거부 주문은 카운트 제외 → 통과
    check_order(conn, s, OrderIntent("005930", "BUY", 1, 100))
