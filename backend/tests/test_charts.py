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
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        kis_paper_account_no="00000000",
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
async def test_weekly_chart_uses_two_year_lookback(tmp_path):
    """주봉은 일봉(~200일)보다 넓은 ~2년 범위를 조회해 100건 상한을 채운다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    ).mock(return_value=httpx.Response(200, json=_WEEKLY_BODY))

    await get_weekly_chart("005930", s)

    params = route.calls.last.request.url.params
    d1 = datetime.strptime(params["FID_INPUT_DATE_1"], "%Y%m%d")
    d2 = datetime.strptime(params["FID_INPUT_DATE_2"], "%Y%m%d")
    assert (d2 - d1).days >= 700  # 약 2년(~100주)


@respx.mock
async def test_daily_chart_uses_200day_lookback(tmp_path):
    """일봉은 ~200일(≈100영업일) 범위를 유지한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    ).mock(return_value=httpx.Response(200, json=_DAILY_BODY))

    await get_daily_chart("005930", s)

    params = route.calls.last.request.url.params
    d1 = datetime.strptime(params["FID_INPUT_DATE_1"], "%Y%m%d")
    d2 = datetime.strptime(params["FID_INPUT_DATE_2"], "%Y%m%d")
    assert 150 <= (d2 - d1).days <= 260


def _patch_now(monkeypatch, *, year=2026, month=6, day=3, hour=10, minute=15) -> None:
    """app.kis.charts의 datetime.now를 고정 KST 시각으로 대체한다(기본 2026-06-03 평일)."""

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return datetime(year, month, day, hour, minute, 0, tzinfo=tz)

    monkeypatch.setattr("app.kis.charts.datetime", _FixedDateTime)


_DAILY_MINUTE_URL = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
_TODAY_MINUTE_URL = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"


def _min_rows(date_str: str, end_hm: str, count: int) -> list[dict]:
    """end_hm(HHMM)부터 1분씩 내려가며 count개의 1분봉 행을 만든다(분 단위)."""
    h, m = int(end_hm[:2]), int(end_hm[2:])
    rows = []
    for i in range(count):
        tm = h * 60 + m - i
        hh, mm = divmod(tm, 60)
        rows.append(
            {
                "stck_bsop_date": date_str,
                "stck_cntg_hour": f"{hh:02d}{mm:02d}00",
                "stck_oprc": "70000",
                "stck_hgpr": "70100",
                "stck_lwpr": "69900",
                "stck_prpr": "70050",
                "cntg_vol": "100",
            }
        )
    return rows


@respx.mock
async def test_today_minute_chart_uses_inquire_time_path(tmp_path, monkeypatch):
    """당일분봉(scope="today")은 FHKST03010200(inquire_time_itemchartprice)을 사용한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(f"{s.rest_base}{_TODAY_MINUTE_URL}").mock(
        return_value=httpx.Response(200, json=_MINUTE_BODY)
    )
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", scope="today", settings=s)

    assert len(candles) == 2
    assert candles[0]["time"] < candles[1]["time"]
    assert route.calls.last.request.headers["tr_id"] == "FHKST03010200"
    # 장중이면 현재 시각, 장외면 마감 시각으로 호출
    assert route.calls.last.request.url.params["FID_INPUT_HOUR_1"] == "101500"  # _patch_now 기본: 10:15


@respx.mock
async def test_today_minute_chart_clamps_to_close_time_outside_market(tmp_path, monkeypatch):
    """장외에는 당일분봉을 마감 시각(15:30)으로 고정해 조회한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(f"{s.rest_base}{_TODAY_MINUTE_URL}").mock(
        return_value=httpx.Response(200, json=_MINUTE_BODY)
    )
    # 장외 시각: 16:30
    _patch_now(monkeypatch, year=2026, month=6, day=3, hour=16, minute=30)

    await get_minute_chart("005930", scope="today", settings=s)

    assert route.calls.last.request.url.params["FID_INPUT_HOUR_1"] == "153000"


@respx.mock
async def test_session_minute_chart_still_uses_dailychart(tmp_path, monkeypatch):
    """scope="session"(기본)일 때는 여전히 FHKST03010230(일별분봉)을 사용한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
        return_value=httpx.Response(200, json=_MINUTE_BODY)
    )
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", scope="session", settings=s)

    assert len(candles) == 2
    assert route.calls.last.request.headers["tr_id"] == "FHKST03010230"


@respx.mock
async def test_minute_chart_uses_dailychart_with_kst_offset(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
        return_value=httpx.Response(200, json=_MINUTE_BODY)
    )
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", settings=s)

    assert len(candles) == 2
    assert candles[0]["time"] < candles[1]["time"]
    assert candles[1]["close"] == 70050
    # 일별분봉(FHKST03010230) 사용 + 거래일 날짜 파라미터
    assert route.calls.last.request.headers["tr_id"] == "FHKST03010230"
    assert route.calls.last.request.url.params["FID_INPUT_DATE_1"] == "20260603"
    # KST 벽시계가 차트축(UTC 표시)에 그대로 보이도록 +9h 보정
    kst = timezone(timedelta(hours=9))
    base = int(datetime(2026, 6, 3, 9, 0, 0, tzinfo=kst).astimezone(timezone.utc).timestamp())
    assert candles[0]["time"] == base + 9 * 3600


@respx.mock
async def test_minute_chart_paginates_until_session_start(tmp_path, monkeypatch):
    """한 세션을 채우기 위해 120건이면 다음 페이지를 이어 조회한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    page1 = _min_rows("20260603", "1530", 120)  # 최소시각 133100 > 090000 → 다음 페이지
    page2 = _min_rows("20260603", "1331", 40)  # 133100부터(1건 중복) 120건 미만 → 종료
    route = respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
        side_effect=[
            httpx.Response(200, json={"rt_cd": "0", "output2": page1}),
            httpx.Response(200, json={"rt_cd": "0", "output2": page2}),
        ]
    )
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", settings=s)

    assert route.call_count == 2  # 페이지네이션 발생
    assert route.calls[0].request.url.params["FID_INPUT_HOUR_1"] == "153000"
    assert route.calls[1].request.url.params["FID_INPUT_HOUR_1"] == "133100"
    # 중복 시각(133100)은 제거되어 120 + 39
    assert len(candles) == 159


@respx.mock
async def test_minute_chart_resamples_to_5min(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _token_mock(s)
    bars = [
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090000", "stck_oprc": "70000", "stck_hgpr": "70100", "stck_lwpr": "69900", "stck_prpr": "70050", "cntg_vol": "100"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090100", "stck_oprc": "70050", "stck_hgpr": "70200", "stck_lwpr": "70000", "stck_prpr": "70150", "cntg_vol": "200"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090200", "stck_oprc": "70150", "stck_hgpr": "70300", "stck_lwpr": "70100", "stck_prpr": "70250", "cntg_vol": "150"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090300", "stck_oprc": "70250", "stck_hgpr": "70150", "stck_lwpr": "70050", "stck_prpr": "70100", "cntg_vol": "120"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090400", "stck_oprc": "70100", "stck_hgpr": "70250", "stck_lwpr": "70080", "stck_prpr": "70200", "cntg_vol": "130"},
        {"stck_bsop_date": "20260603", "stck_cntg_hour": "090500", "stck_oprc": "70200", "stck_hgpr": "70260", "stck_lwpr": "70180", "stck_prpr": "70220", "cntg_vol": "90"},
    ]
    respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output2": bars})
    )
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", 5, settings=s)

    assert len(candles) == 2  # 09:00~09:04 한 버킷 + 09:05 한 버킷
    a = candles[0]
    assert a["open"] == 70000  # 첫 봉
    assert a["high"] == 70300  # 최고
    assert a["low"] == 69900  # 최저
    assert a["close"] == 70200  # 09:04 종가
    assert a["volume"] == 700  # 100+200+150+120+130
    assert candles[1]["open"] == 70200 and candles[1]["volume"] == 90


@respx.mock
async def test_minute_chart_falls_back_to_previous_trading_day(tmp_path, monkeypatch):
    """오늘이 휴장(빈 응답)이면 직전 거래일로 거슬러 조회한다."""
    s = _settings(tmp_path)
    _token_mock(s)

    def _by_date(request):
        d = request.url.params["FID_INPUT_DATE_1"]
        if d == "20260603":  # 오늘=빈 결과(휴장 가정)
            return httpx.Response(200, json={"rt_cd": "0", "output2": []})
        return httpx.Response(200, json=_MINUTE_BODY)

    route = respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(side_effect=_by_date)
    _patch_now(monkeypatch)

    candles = await get_minute_chart("005930", settings=s)

    assert len(candles) == 2
    used_dates = [c.request.url.params["FID_INPUT_DATE_1"] for c in route.calls]
    assert "20260602" in used_dates  # 직전 거래일로 폴백


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
async def test_daily_chart_caches_within_ttl(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    ).mock(return_value=httpx.Response(200, json=_DAILY_BODY))

    first = await get_daily_chart("005930", s)
    second = await get_daily_chart("005930", s)

    assert first == second
    assert route.call_count == 1  # 두 번째는 캐시 히트 → KIS 재호출 없음


@respx.mock
async def test_empty_chart_is_not_cached(tmp_path):
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(
        f"{s.rest_base}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    ).mock(return_value=httpx.Response(200, json={"rt_cd": "0", "output2": []}))

    await get_daily_chart("005930", s)
    await get_daily_chart("005930", s)

    assert route.call_count == 2  # 빈 결과는 캐시하지 않으므로 매번 재호출


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
def test_chart_router_minute_unit(tmp_path):
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
            return_value=httpx.Response(200, json=_MINUTE_BODY)
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=minute&unit=5")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["interval"] == "minute"
        assert data["unit"] == 5
    finally:
        app.dependency_overrides.clear()


def test_chart_router_bad_unit():
    with TestClient(app) as client:
        res = client.get("/api/charts/005930?interval=minute&unit=3")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_UNIT"


@respx.mock
def test_chart_router_minute_scope_today(tmp_path):
    """분봉 API에 scope=today를 전달하면 응답에 포함된다."""
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}{_TODAY_MINUTE_URL}").mock(
            return_value=httpx.Response(200, json=_MINUTE_BODY)
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=minute&scope=today")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["interval"] == "minute"
        assert data["scope"] == "today"
        assert len(data["candles"]) == 2
    finally:
        app.dependency_overrides.clear()


@respx.mock
def test_chart_router_minute_scope_session_default(tmp_path):
    """scope을 명시하지 않으면 session이 기본값이다."""
    s = _settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: s
    try:
        _token_mock(s)
        respx.get(f"{s.rest_base}{_DAILY_MINUTE_URL}").mock(
            return_value=httpx.Response(200, json=_MINUTE_BODY)
        )
        with TestClient(app) as client:
            res = client.get("/api/charts/005930?interval=minute")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["scope"] == "session"
    finally:
        app.dependency_overrides.clear()


def test_chart_router_bad_scope():
    """잘못된 scope은 400 BAD_SCOPE를 반환한다."""
    with TestClient(app) as client:
        res = client.get("/api/charts/005930?interval=minute&scope=invalid")
    assert res.status_code == 400
    assert res.json()["code"] == "BAD_SCOPE"


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
