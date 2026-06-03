"""종목 차트(일봉/분봉) 조회 테스트(HTTP는 respx로 mock)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.kis.charts import ChartUnavailableError, get_daily_chart, get_minute_chart
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


def _token_mock(s: Settings) -> None:
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )


_DAILY_BODY = {
    "rt_cd": "0",
    "output2": [
        {"stck_bsop_date": "20260602", "stck_oprc": "70000", "stck_hgpr": "71000", "stck_lwpr": "69500", "stck_clpr": "70500", "acml_vol": "12000000"},
        {"stck_bsop_date": "20260601", "stck_oprc": "69000", "stck_hgpr": "70000", "stck_lwpr": "68800", "stck_clpr": "69800", "acml_vol": "9000000"},
        {"stck_bsop_date": "", "stck_clpr": "0"},
    ],
}

_MINUTE_BODY = {
    "rt_cd": "0",
    "output2": [
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090100", "stck_oprc": "70000", "stck_hgpr": "70100", "stck_lwpr": "69900", "stck_prpr": "70050", "cntg_vol": "1500"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090000", "stck_oprc": "69950", "stck_hgpr": "70050", "stck_lwpr": "69900", "stck_prpr": "70000", "cntg_vol": "2000"},
    ],
}


@respx.mock
async def test_일봉_파싱_정렬(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(200, json=_DAILY_BODY)
    )

    candles = await get_daily_chart("005930", s)

    assert len(candles) == 2
    assert candles[0]["time"] == "2026-06-01"
    assert candles[1]["time"] == "2026-06-02"
    assert candles[1]["close"] == 70500
    assert candles[1]["volume"] == 12000000


@respx.mock
async def test_분봉_파싱_unix초(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice").mock(
        return_value=httpx.Response(200, json=_MINUTE_BODY)
    )

    candles = await get_minute_chart("005930", s)

    assert len(candles) == 2
    assert candles[0]["time"] < candles[1]["time"]
    assert isinstance(candles[0]["time"], int)
    assert candles[1]["close"] == 70050

    kst = timezone(timedelta(hours=9))
    expected = int(datetime(2026, 6, 3, 9, 0, 0, tzinfo=kst).astimezone(timezone.utc).timestamp())
    assert candles[0]["time"] == expected


@respx.mock
async def test_일봉_HTTP오류시_예외(tmp_path):
    """일시적 5xx는 빈 리스트가 아니라 ChartUnavailableError로 전파한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(500, json={"msg1": "server error"})
    )

    with pytest.raises(ChartUnavailableError):
        await get_daily_chart("005930", s)


@respx.mock
async def test_일봉_rt_cd오류시_예외(tmp_path):
    """HTTP 200이라도 rt_cd!=0이면 ChartUnavailableError로 전파한다(데이터 없음과 구분)."""
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(
            200, json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "조회할 수 없는 종목"}
        )
    )

    with pytest.raises(ChartUnavailableError):
        await get_daily_chart("005930", s)


@respx.mock
async def test_일봉_빈데이터는_빈리스트(tmp_path):
    """정상 응답(rt_cd=0)인데 데이터가 없으면 예외가 아니라 빈 리스트를 반환한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output2": []})
    )

    candles = await get_daily_chart("005930", s)

    assert candles == []


@respx.mock
def test_차트_라우터_일봉(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
            return_value=httpx.Response(200, json=_DAILY_BODY)
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=daily")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["interval"] == "daily"
        assert len(data["candles"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_차트_라우터_잘못된interval():
    with TestClient(app) as client:
        res = client.get("/api/charts/005930?interval=hourly")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_INTERVAL"


@respx.mock
def test_차트_라우터_일시오류시_503(tmp_path):
    """KIS 일시 오류는 빈 캔들(200)이 아니라 503 CHART_UNAVAILABLE로 응답한다."""
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(
            f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        ).mock(
            return_value=httpx.Response(
                200, json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "일시 오류"}
            )
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=daily")
        assert res.status_code == 503
        assert res.json()["code"] == "CHART_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()
