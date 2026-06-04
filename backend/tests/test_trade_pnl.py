"""기간별 매매손익 계산·엔드포인트 테스트."""

from __future__ import annotations

import sqlite3

import httpx
import pytest
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.db.database import connect, get_db, init_db
from app.main import app
from app.services import order_service, trade_pnl_service
from app.services.trade_pnl_service import ESTIMATED_FEE_RATE, ESTIMATED_TAX_RATE


def _db(tmp_path) -> sqlite3.Connection:
    path = str(tmp_path / "t.db")
    init_db(path)
    return connect(path)


def _fill(conn, symbol, side, qty, price, created_at):
    """체결 주문을 직접 삽입(created_at 지정)."""
    conn.execute(
        "INSERT INTO orders (symbol, side, qty, filled_qty, remaining_qty, price, mode, status, created_at) "
        "VALUES (?, ?, ?, ?, 0, ?, 'paper', 'filled', ?)",
        (symbol, side, qty, qty, price, created_at),
    )
    conn.commit()


def test_매도마다_실현손익_행_생성(tmp_path):
    conn = _db(tmp_path)
    # 10주 @1000 매수 후 10주 @1500 매도 → 매도 1행
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 10, 1500, "2026-06-02 10:00:00")

    res = trade_pnl_service.compute_trade_pnl(conn, mode="paper")
    assert len(res["rows"]) == 1
    r = res["rows"][0]
    assert r["symbol"] == "005930"
    assert r["sell_qty"] == 10
    assert r["buy_amount"] == 10000
    assert r["sell_amount"] == 15000
    # 실현 = 15000 - 10000 - 수수료 - 세금
    fee = round(10000 * ESTIMATED_FEE_RATE) + round(15000 * ESTIMATED_FEE_RATE)
    tax = round(15000 * ESTIMATED_TAX_RATE)
    assert r["realized_pnl"] == 15000 - 10000 - fee - tax
    assert r["source"] == "bot"  # 로컬 계산은 전부 봇
    assert res["estimated"] is True
    assert res["source"] == "local"


def test_봇직접_분류_annotate(tmp_path):
    conn = _db(tmp_path)
    # 봇이 005930을 2026-06-02에 매도 체결 → 그 (종목,날짜)는 '봇'
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 10, 1500, "2026-06-02 10:00:00")
    rows = [
        {"symbol": "005930", "trade_date": "2026-06-02"},  # 봇이 판 날
        {"symbol": "005930", "trade_date": "2026-06-03"},  # 봇이 안 판 날 → 직접
        {"symbol": "000660", "trade_date": "2026-06-02"},  # 봇이 안 판 종목 → 직접
    ]
    trade_pnl_service.annotate_source(conn, "paper", rows)
    assert [r["source"] for r in rows] == ["bot", "manual", "manual"]


def test_평균원가법_부분매도(tmp_path):
    conn = _db(tmp_path)
    # 10주 @1000, 10주 @2000 매수(평균 1500) → 5주 @1800 매도
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "BUY", 10, 2000, "2026-06-01 11:00:00")
    _fill(conn, "005930", "SELL", 5, 1800, "2026-06-02 10:00:00")

    res = trade_pnl_service.compute_trade_pnl(conn, mode="paper")
    r = res["rows"][0]
    assert r["buy_unit_price"] == 1500  # 평균원가
    assert r["buy_amount"] == 7500  # 1500*5
    assert r["sell_amount"] == 9000  # 1800*5


def test_기간_필터_및_정렬(tmp_path):
    conn = _db(tmp_path)
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 5, 1100, "2026-06-02 10:00:00")
    _fill(conn, "005930", "SELL", 5, 1200, "2026-06-05 10:00:00")

    # 기간 06-03~06-30 → 06-05 매도 1건만
    res = trade_pnl_service.compute_trade_pnl(conn, mode="paper", start="2026-06-03", end="2026-06-30")
    assert len(res["rows"]) == 1
    assert res["rows"][0]["trade_date"] == "2026-06-05"

    # 역순(기본): 최신 먼저
    res_all = trade_pnl_service.compute_trade_pnl(conn, mode="paper", sort="desc")
    assert [r["trade_date"] for r in res_all["rows"]] == ["2026-06-05", "2026-06-02"]
    res_asc = trade_pnl_service.compute_trade_pnl(conn, mode="paper", sort="asc")
    assert [r["trade_date"] for r in res_asc["rows"]] == ["2026-06-02", "2026-06-05"]


def test_종목별_필터(tmp_path):
    conn = _db(tmp_path)
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 10, 1100, "2026-06-02 10:00:00")
    _fill(conn, "000660", "BUY", 5, 2000, "2026-06-01 11:00:00")
    _fill(conn, "000660", "SELL", 5, 2200, "2026-06-02 11:00:00")

    res = trade_pnl_service.compute_trade_pnl(conn, mode="paper", symbol="000660")
    assert len(res["rows"]) == 1
    assert res["rows"][0]["symbol"] == "000660"
    # 요약도 해당 종목만 반영
    assert res["summary"]["sell"]["amount"] == 11000  # 2200*5


def test_요약_매도매수합계(tmp_path):
    conn = _db(tmp_path)
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 10, 1500, "2026-06-02 10:00:00")

    res = trade_pnl_service.compute_trade_pnl(conn, mode="paper")
    s = res["summary"]
    assert s["sell"]["qty"] == 10
    assert s["sell"]["amount"] == 15000
    assert s["buy"]["amount"] == 10000
    assert s["realized_pnl_total"] == res["rows"][0]["realized_pnl"]
    assert s["total_pnl_rate"] != 0


def test_모드_격리(tmp_path):
    conn = _db(tmp_path)
    _fill(conn, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(conn, "005930", "SELL", 10, 1500, "2026-06-02 10:00:00")
    # live 모드는 체결이 없으므로 빈 결과
    res_live = trade_pnl_service.compute_trade_pnl(conn, mode="live")
    assert res_live["rows"] == []
    assert res_live["summary"]["realized_pnl_total"] == 0


@pytest.fixture()
def client(tmp_path):
    path = str(tmp_path / "api.db")
    init_db(path)
    settings = Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
    )

    def _override_db():
        conn = connect(path)
        try:
            yield conn
        finally:
            conn.close()

    # 시드 데이터
    seed = connect(path)
    _fill(seed, "005930", "BUY", 10, 1000, "2026-06-01 10:00:00")
    _fill(seed, "005930", "SELL", 10, 1500, "2026-06-02 10:00:00")
    seed.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = _override_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_엔드포인트_조회(client):
    res = client.get("/api/trade-pnl?mode=paper")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["rows"]) == 1
    assert data["estimated"] is True


def test_엔드포인트_잘못된_날짜(client):
    res = client.get("/api/trade-pnl?mode=paper&start=2026/06/01")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_DATE"


def test_엔드포인트_잘못된_모드(client):
    res = client.get("/api/trade-pnl?mode=xxx")
    assert res.status_code == 400


@respx.mock
def test_live_KIS_경로(tmp_path):
    settings = Settings(
        _env_file=None,
        trading_mode="live",
        kis_live_app_key="k",
        kis_live_app_secret="s",
        kis_live_account_no="12345678",
        database_path=str(tmp_path / "live.db"),
    )
    init_db(settings.database_path)
    base = settings.kis_for("live").rest_base
    respx.post(f"{base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(f"{base}/uapi/domestic-stock/v1/trading/inquire-period-trade-profit").mock(
        return_value=httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "output1": [
                    {
                        "trad_dt": "20260604",
                        "pdno": "005930",
                        "prdt_name": "삼성전자",
                        "sll_qty": "10",
                        "pchs_unpr": "1000",
                        "sll_pric": "1500",
                        "buy_amt": "10000",
                        "sll_amt": "15000",
                        "fee": "5",
                        "tl_tax": "22",
                        "rlzt_pfls": "4973",
                        "pfls_rt": "49.73",
                    }
                ],
                "output2": {"tot_rlzt_pfls": "4973", "tot_pftrt": "49.73"},
            },
        )
    )

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = lambda: connect(settings.database_path)
    try:
        with TestClient(app) as c:
            res = c.get("/api/trade-pnl?mode=live&start=2026-06-01&end=2026-06-04")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["source"] == "kis"
        assert data["estimated"] is False
        assert data["available"] is True
        assert len(data["rows"]) == 1
        assert data["rows"][0]["symbol"] == "005930"
        assert data["rows"][0]["trade_date"] == "2026-06-04"
        assert data["rows"][0]["realized_pnl"] == 4973
        # 봇 주문 이력이 없는 계좌 → KIS 매매는 직접(manual)로 분류
        assert data["rows"][0]["source"] == "manual"
        assert data["summary"]["realized_pnl_total"] == 4973
    finally:
        app.dependency_overrides.clear()
