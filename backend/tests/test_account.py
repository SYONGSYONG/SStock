"""계좌 잔고 조회 테스트 (HTTP는 respx로 mock)."""

from __future__ import annotations

import httpx
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.kis.orders import get_account_summary
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


_BALANCE_OUTPUT2 = {
    "rt_cd": "0",
    "output1": [],
    "output2": [
        {
            "dnca_tot_amt": "9500000",
            "prvs_rcdl_excc_amt": "9480000",
            "pchs_amt_smtl_amt": "500000",
            "evlu_amt_smtl_amt": "520000",
            "evlu_pfls_smtl_amt": "20000",
            "tot_evlu_amt": "10000000",
            "nass_amt": "10000000",
        }
    ],
}


@respx.mock
async def test_계좌요약_파싱(tmp_path):
    s = _settings(tmp_path)
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
        return_value=httpx.Response(200, json=_BALANCE_OUTPUT2)
    )
    summary = await get_account_summary(s)

    assert summary["deposit"] == 9500000
    assert summary["orderable_cash"] == 9480000
    assert summary["eval_pnl"] == 20000
    assert summary["total_eval"] == 10000000
    assert summary["net_asset"] == 10000000


@respx.mock
async def test_계좌요약_output2_dict_허용(tmp_path):
    """일부 응답은 output2가 단일 dict로 올 수 있다."""
    s = _settings(tmp_path)
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )
    body = {**_BALANCE_OUTPUT2, "output2": _BALANCE_OUTPUT2["output2"][0]}
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
        return_value=httpx.Response(200, json=body)
    )
    summary = await get_account_summary(s)

    assert summary["deposit"] == 9500000


@respx.mock
def test_잔고_엔드포인트_정상(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
            return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
        )
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
            return_value=httpx.Response(200, json=_BALANCE_OUTPUT2)
        )
        with TestClient(app) as client:
            res = client.get("/api/account/balance")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["available"] is True
        assert data["deposit"] == 9500000
    finally:
        app.dependency_overrides.clear()


def test_토큰_프리워밍_테스트환경에서_꺼짐():
    """conftest가 KIS_TOKEN_PREWARM=0으로 끈다(TestClient 기동 시 실KIS 호출 방지)."""
    assert get_settings().kis_token_prewarm is False


def test_토큰_프리워밍_기본값은_켜짐(monkeypatch):
    """환경변수가 없으면 기본값은 True(실서버 기동 시 프리워밍)."""
    monkeypatch.delenv("KIS_TOKEN_PREWARM", raising=False)
    assert Settings(_env_file=None).kis_token_prewarm is True


@respx.mock
def test_잔고_엔드포인트_KIS오류시_graceful(tmp_path):
    """KIS가 5xx여도 500 대신 available=false로 응답한다."""
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
            return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
        )
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
            return_value=httpx.Response(500, json={"msg1": "서버 오류"})
        )
        with TestClient(app) as client:
            res = client.get("/api/account/balance")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["available"] is False
        assert data["deposit"] is None
    finally:
        app.dependency_overrides.clear()


@respx.mock
def test_잔고_엔드포인트_rt_cd오류시_조회불가(tmp_path):
    """HTTP 200이라도 rt_cd≠0(예: 잘못된 계좌)이면 available=false(침묵 실패 방지)."""
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
            return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
        )
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/trading/inquire-balance").mock(
            return_value=httpx.Response(
                200,
                json={"rt_cd": "2", "msg_cd": "OPSQ2000", "msg1": "INVALID_CHECK_ACNO", "output2": []},
            )
        )
        with TestClient(app) as client:
            res = client.get("/api/account/balance")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["available"] is False
        assert data["deposit"] is None
    finally:
        app.dependency_overrides.clear()
