"""종목 차트(일봉/주봉/분봉) 조회 테스트."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.kis.charts import ChartUnavailableError, get_daily_chart, get_minute_chart, get_weekly_chart
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
        {
            "stck_bsop_date": "20260602",
            "stck_oprc": "70000",
            "stck_hgpr": "71000",
            "stck_lwpr": "69500",
            "stck_clpr": "70500",
            "acml_vol": "12000000",
        },
        {
            "stck_bsop_date": "20260601",
            "stck_oprc": "69000",
            "stck_hgpr": "70000",
            "stck_lwpr": "68800",
            "stck_clpr": "69800",
            "acml_vol": "9000000",
        },
        {"stck_bsop_date": "", "stck_clpr": "0"},
    ],
}

_WEEKLY_BODY = {
    "rt_cd": "0",
    "output2": [
        {
            "stck_bsop_date": "20260606",
            "stck_oprc": "68000",
            "stck_hgpr": "71500",
            "stck_lwpr": "67500",
            "stck_clpr": "70500",
            "acml_vol": "55000000",
        },
        {
            "stck_bsop_date": "20260530",
            "stck_oprc": "66000",
            "stck_hgpr": "69000",
            "stck_lwpr": "65500",
            "stck_clpr": "68000",
            "acml_vol": "41000000",
        },
    ],
}

_MINUTE_BODY = {
    "rt_cd": "0",
    "output2": [
        {
            "stck_bsop_date": "20260603",
            "stck_cntg_hour": "090100",
            "stck_oprc": "70000",
            "stck_hgpr": "70100",
            "stck_lwpr": "69900",
            "stck_prpr": "70050",
            "cntg_vol": "1500",
        },
        {
            "stck_bsop_date": "20260603",
            "stck_cntg_hour": "090000",
            "stck_oprc": "69950",
            "stck_hgpr": "70050",
            "stck_lwpr": "69900",
            "stck_prpr": "70000",
            "cntg_vol": "2000",
        },
    ],
}


@respx.mock
async def test_daily_chart_parses(tmp_path):
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
async def test_weekly_chart_parses(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(200, json=_WEEKLY_BODY)
    )

    candles = await get_weekly_chart("005930", s)

    assert len(candles) == 2
    assert candles[0]["time"] == "2026-05-30"
    assert candles[1]["time"] == "2026-06-06"
    assert candles[1]["close"] == 70500
    assert candles[1]["volume"] == 55000000


@respx.mock
async def test_minute_chart_returns_unix_seconds(tmp_path):
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

    # 분봉 타임스탬프는 KST 벽시계가 차트축(UTC 표시)에 그대로 보이도록 +9h 보정한다.
    kst = timezone(timedelta(hours=9))
    base = int(datetime(2026, 6, 3, 9, 0, 0, tzinfo=kst).astimezone(timezone.utc).timestamp())
    assert candles[0]["time"] == base + 9 * 3600


def _patch_now(monkeypatch, *, hour: int, minute: int) -> None:
    """app.kis.charts의 datetime.now를 고정 KST 시각으로 대체한다."""

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(2026, 6, 3, hour, minute, 0, tzinfo=tz)

    monkeypatch.setattr("app.kis.charts.datetime", _FixedDateTime)


@respx.mock
async def test_minute_chart_uses_now_during_market_hours(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    ).mock(return_value=httpx.Response(200, json=_MINUTE_BODY))
    _patch_now(monkeypatch, hour=10, minute=15)

    await get_minute_chart("005930", s)

    assert route.calls.last.request.url.params["FID_INPUT_HOUR_1"] == "101500"


@respx.mock
async def test_minute_chart_clamps_to_close_after_hours(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"
    ).mock(return_value=httpx.Response(200, json=_MINUTE_BODY))
    _patch_now(monkeypatch, hour=16, minute=49)

    await get_minute_chart("005930", s)

    assert route.calls.last.request.url.params["FID_INPUT_HOUR_1"] == "153000"


@respx.mock
async def test_daily_chart_http_error_raises(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(500, json={"msg1": "server error"})
    )

    with pytest.raises(ChartUnavailableError):
        await get_daily_chart("005930", s)


@respx.mock
async def test_daily_chart_rt_cd_error_raises(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(
            200, json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "조회 불가 종목"}
        )
    )

    with pytest.raises(ChartUnavailableError):
        await get_daily_chart("005930", s)


@respx.mock
async def test_daily_chart_empty_body_returns_empty_list(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output2": []})
    )

    candles = await get_daily_chart("005930", s)

    assert candles == []


@respx.mock
def test_chart_router_daily(tmp_path):
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


@respx.mock
def test_chart_router_weekly(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
            return_value=httpx.Response(200, json=_WEEKLY_BODY)
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=weekly")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["interval"] == "weekly"
        assert len(data["candles"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_chart_router_bad_interval():
    with TestClient(app) as client:
        res = client.get("/api/charts/005930?interval=hourly")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_INTERVAL"


@respx.mock
def test_chart_router_kis_error_503(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice").mock(
            return_value=httpx.Response(200, json={"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "일시 오류"})
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=daily")
        assert res.status_code == 503
        assert res.json()["code"] == "CHART_UNAVAILABLE"
    finally:
        app.dependency_overrides.clear()
