"""KIS 종목 차트(일봉/분봉) 조회.

- 일봉: 국내주식 기간별시세(inquire-daily-itemchartprice, FHKST03010100)
- 분봉: 주식당일분봉조회(inquire-time-itemchartprice, FHKST03010200)

시세 조회와 동일하게, KIS 일시 실패 시 예외를 전파하지 않고 빈 캔들 리스트를
반환한다(차트 모달은 "데이터 없음" 안내). 캔들은 시간 오름차순으로 정렬한다.

반환 캔들 형식(lightweight-charts 호환):
- 일봉  time = "YYYY-MM-DD"
- 분봉  time = UNIX 초(KST 벽시계를 UTC로 환산 → 축이 KST HH:MM 표기)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import QUOTE_TR_IDS
from app.kis.numbers import to_int

logger = logging.getLogger(__name__)

_DAILY_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
_MINUTE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"

_KST = timezone(timedelta(hours=9))
_DAILY_LOOKBACK_DAYS = 200  # ~100 영업일 확보용 달력일


def _ohlcv(oprc: Any, hgpr: Any, lwpr: Any, close: Any, vol: Any) -> dict[str, Any] | None:
    """OHLCV를 int로 변환. 핵심 값이 비면 None(해당 캔들 제외)."""
    o, h, low, c = to_int(oprc), to_int(hgpr), to_int(lwpr), to_int(close)
    if None in (o, h, low, c):
        return None
    return {"open": o, "high": h, "low": low, "close": c, "volume": to_int(vol) or 0}


def _parse_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for r in rows:
        date = (r.get("stck_bsop_date") or "").strip()
        if len(date) != 8:
            continue
        body = _ohlcv(
            r.get("stck_oprc"), r.get("stck_hgpr"), r.get("stck_lwpr"),
            r.get("stck_clpr"), r.get("acml_vol"),
        )
        if body is None:
            continue
        candles.append({"time": f"{date[0:4]}-{date[4:6]}-{date[6:8]}", **body})
    candles.sort(key=lambda c: c["time"])  # 오름차순
    return candles


def _parse_minute(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for r in rows:
        date = (r.get("stck_bsop_date") or "").strip()
        hms = (r.get("stck_cntg_hour") or "").strip()
        if len(date) != 8 or len(hms) != 6:
            continue
        body = _ohlcv(
            r.get("stck_oprc"), r.get("stck_hgpr"), r.get("stck_lwpr"),
            r.get("stck_prpr"), r.get("cntg_vol"),
        )
        if body is None:
            continue
        # KST 벽시계 숫자를 UTC로 환산해 차트 축이 KST HH:MM을 그대로 표기하게 함
        dt = datetime(
            int(date[0:4]), int(date[4:6]), int(date[6:8]),
            int(hms[0:2]), int(hms[2:4]), int(hms[4:6]), tzinfo=timezone.utc,
        )
        candles.append({"time": int(dt.timestamp()), **body})
    candles.sort(key=lambda c: c["time"])
    return candles


async def get_daily_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """일봉(최근 ~100영업일) 캔들. KIS 오류 시 빈 리스트."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    today = datetime.now(_KST).date()
    start = today - timedelta(days=_DAILY_LOOKBACK_DAYS)
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
        "FID_INPUT_DATE_2": today.strftime("%Y%m%d"),
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "1",
    }
    try:
        data = await client.get(_DAILY_PATH, QUOTE_TR_IDS["inquire_daily_itemchartprice"], params)
    except httpx.HTTPError as exc:
        logger.warning("일봉 조회 실패 %s: %s", symbol, exc)
        return []
    return _parse_daily(data.get("output2") or [])


async def get_minute_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """당일 분봉 캔들. KIS 오류 시 빈 리스트."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    now_hms = datetime.now(_KST).strftime("%H%M%S")
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": now_hms,
        "FID_PW_DATA_INCU_YN": "Y",
        "FID_ETC_CLS_CODE": "",
    }
    try:
        data = await client.get(_MINUTE_PATH, QUOTE_TR_IDS["inquire_time_itemchartprice"], params)
    except httpx.HTTPError as exc:
        logger.warning("분봉 조회 실패 %s: %s", symbol, exc)
        return []
    return _parse_minute(data.get("output2") or [])
