"""주문/포지션 라우터 테스트."""

from __future__ import annotations

import httpx
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="00000000",
        database_path=str(tmp_path / "sstock.db"),
    )


@respx.mock
def test_포지션_잔고기반(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
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
                            "hldg_qty": "10",
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
