"""일일 주문 한도 서비스·엔드포인트 테스트."""

from __future__ import annotations

import sqlite3

import pytest
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.db.database import connect, get_db, init_db
from app.main import app
from app.services import order_service, risk_limit_service


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "test.db")
    init_db(path)
    return connect(path)


def _settings(**kw) -> Settings:
    base = dict(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        daily_max_orders=100,
        daily_max_amount=1_000_000,
    )
    base.update(kw)
    return Settings(**base)


def test_미설정시_기본값_폴백(tmp_path):
    conn = _db(tmp_path)
    limits = risk_limit_service.get_limits(conn, _settings(), "paper")
    assert limits == {"max_orders": 100, "max_amount": 1_000_000, "max_daily_loss": 0}


def test_한도_설정_조회_왕복(tmp_path):
    conn = _db(tmp_path)
    risk_limit_service.set_limits(conn, "paper", 50, 5_000_000)
    limits = risk_limit_service.get_limits(conn, _settings(), "paper")
    assert limits == {"max_orders": 50, "max_amount": 5_000_000, "max_daily_loss": 0}
    # 설정한 모드만 영향 — live는 여전히 기본값
    assert risk_limit_service.get_limits(conn, _settings(), "live")["max_orders"] == 100


def test_한도_변경은_upsert(tmp_path):
    conn = _db(tmp_path)
    risk_limit_service.set_limits(conn, "paper", 50, 5_000_000)
    risk_limit_service.set_limits(conn, "paper", 200, 9_000_000)
    assert risk_limit_service.get_limits(conn, _settings(), "paper") == {
        "max_orders": 200,
        "max_amount": 9_000_000,
        "max_daily_loss": 0,
    }


def test_당일_사용량_집계(tmp_path):
    conn = _db(tmp_path)
    # 거부 주문은 사용량에서 제외, 체결/요청 주문만 집계
    order_service.save_order(conn, "005930", "BUY", 2, 1000, "paper", status="filled")
    order_service.save_order(conn, "005930", "BUY", 1, 5000, "paper", status="requested")
    order_service.save_order(conn, "005930", "BUY", 9, 9999, "paper", status="rejected")
    assert risk_limit_service.today_order_count(conn, "paper") == 2
    assert risk_limit_service.today_order_amount(conn, "paper") == 2 * 1000 + 1 * 5000


def test_status_한도와_사용량_함께(tmp_path):
    conn = _db(tmp_path)
    risk_limit_service.set_limits(conn, "paper", 30, 3_000_000)
    order_service.save_order(conn, "005930", "BUY", 1, 1000, "paper", status="filled")
    st = risk_limit_service.status(conn, _settings(), "paper")
    assert st == {
        "mode": "paper",
        "max_orders": 30,
        "max_amount": 3_000_000,
        "max_daily_loss": 0,
        "order_count": 1,
        "order_amount": 1000,
        "realized_pnl": 0,
    }


@pytest.fixture()
def client(tmp_path):
    path = str(tmp_path / "api.db")
    settings = _settings(database_path=path)
    init_db(path)

    def _override_db():
        conn = connect(path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = _override_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_엔드포인트_조회_기본값(client):
    res = client.get("/api/risk-limits?mode=paper")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["max_orders"] == 100
    assert data["order_count"] == 0


def test_엔드포인트_변경후_조회(client):
    res = client.put("/api/risk-limits?mode=paper", json={"max_orders": 77, "max_amount": 7_000_000})
    assert res.status_code == 200
    assert res.json()["data"]["max_orders"] == 77
    res2 = client.get("/api/risk-limits?mode=paper")
    assert res2.json()["data"]["max_orders"] == 77
    assert res2.json()["data"]["max_amount"] == 7_000_000


def test_엔드포인트_잘못된_모드(client):
    res = client.get("/api/risk-limits?mode=xxx")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_MODE"


def test_엔드포인트_유효성_검증(client):
    res = client.put("/api/risk-limits?mode=paper", json={"max_orders": 0, "max_amount": 100})
    assert res.status_code == 422
