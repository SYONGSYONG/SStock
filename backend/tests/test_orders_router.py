"""주문/포지션 라우터 테스트."""

from __future__ import annotations

import httpx
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.db.database import connect, get_db, init_db
from app.main import app
from app.services import order_service


def _use_db(s: Settings):
    """positions 라우터가 테스트 DB를 읽도록 get_db 의존성을 오버라이드한다."""
    init_db(s.database_path)

    def _override():
        conn = connect(s.database_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = _override


def _balance_mock(s: Settings, hldg_qty: str = "10") -> None:
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
        return_value=httpx.Response(
            200,
            json={
                "rt_cd": "0",
                "output1": [
                    {
                        "pdno": "005930",
                        "prdt_name": "삼성전자",
                        "hldg_qty": hldg_qty,
                        "pchs_avg_pric": "68000",
                        "prpr": "70000",
                        "evlu_amt": "700000",
                        "evlu_pfls_amt": "20000",
                        "evlu_pfls_rt": "2.94",
                    }
                ],
            },
        )
    )


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        kis_paper_account_no="00000000",
        database_path=str(tmp_path / "sstock.db"),
    )


@respx.mock
def test_포지션_잔고기반(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    _use_db(s)
    try:
        _balance_mock(s)
        with TestClient(app) as client:
            res = client.get("/api/positions")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["symbol"] == "005930"
        assert data[0]["qty"] == 10
        assert data[0]["avg_price"] == 68000
        assert data[0]["eval_amount"] == 700000
        assert data[0]["pl_amount"] == 20000
        # 봇 주문 이력이 없으므로 전량 직접 매수분
        assert data[0]["source"] == "manual"
        assert data[0]["bot_qty"] == 0
        assert data[0]["manual_qty"] == 10
    finally:
        app.dependency_overrides.clear()


@respx.mock
def test_포지션_봇직접_혼합_구분(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    _use_db(s)
    try:
        # 실제 잔고 10주 중 봇이 4주 매수 → 봇 4 / 직접 6 = 혼합
        conn = connect(s.database_path)
        order_service.save_order(conn, "005930", "BUY", 4, 68000, "paper", status="filled")
        conn.close()

        _balance_mock(s)
        with TestClient(app) as client:
            res = client.get("/api/positions?mode=paper")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data[0]["source"] == "mixed"
        assert data[0]["bot_qty"] == 4
        assert data[0]["manual_qty"] == 6
    finally:
        app.dependency_overrides.clear()


@respx.mock
def test_포지션_조회실패시_빈목록(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
            return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
        )
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
            return_value=httpx.Response(500, json={"msg1": "server error"})
        )
        with TestClient(app) as client:
            res = client.get("/api/positions")
        assert res.status_code == 200
        assert res.json()["data"] == []
    finally:
        app.dependency_overrides.clear()
