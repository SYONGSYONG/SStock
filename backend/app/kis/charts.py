"""KIS 종목 차트(일봉/주봉/분봉) 조회."""

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


class ChartUnavailableError(RuntimeError):
    """KIS 오류로 차트를 가져오지 못했을 때 발생한다."""


_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
_MINUTE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"

_KST = timezone(timedelta(hours=9))
_KST_OFFSET_SEC = 9 * 3600  # 분봉 타임스탬프를 차트축에 KST 벽시계로 노출하기 위한 보정
_LOOKBACK_DAYS = 200

# 국내 정규장: 09:00 ~ 15:30 (KST)
_MARKET_OPEN_MIN = 9 * 60
_MARKET_CLOSE_MIN = 15 * 60 + 30
_MARKET_CLOSE_HMS = "153000"


def _ohlcv(oprc: Any, hgpr: Any, lwpr: Any, close: Any, vol: Any) -> dict[str, Any] | None:
    close_int = to_int(close)
    if close_int is None:
        return None
    return {
        "open": to_int(oprc) or close_int,
        "high": to_int(hgpr) or close_int,
        "low": to_int(lwpr) or close_int,
        "close": close_int,
        "volume": to_int(vol) or 0,
    }


def _parse_period_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for r in rows:
        date = (r.get("stck_bsop_date") or "").strip()
        if len(date) != 8:
            continue
        body = _ohlcv(
            r.get("stck_oprc"),
            r.get("stck_hgpr"),
            r.get("stck_lwpr"),
            r.get("stck_clpr"),
            r.get("acml_vol"),
        )
        if body is None:
            continue
        candles.append({"time": f"{date[0:4]}-{date[4:6]}-{date[6:8]}", **body})
    candles.sort(key=lambda c: c["time"])
    return candles


def _parse_minute_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for r in rows:
        date = (r.get("stck_bsop_date") or "").strip()
        hms = (r.get("stck_cntg_hour") or "").strip()
        if len(date) != 8 or len(hms) < 4:
            continue
        if len(hms) == 4:
            hms += "00"

        body = _ohlcv(
            r.get("stck_oprc"),
            r.get("stck_hgpr"),
            r.get("stck_lwpr"),
            r.get("stck_prpr"),
            r.get("cntg_vol"),
        )
        if body is None:
            continue
        try:
            dt_kst = datetime(
                int(date[0:4]),
                int(date[4:6]),
                int(date[6:8]),
                int(hms[0:2]),
                int(hms[2:4]),
                int(hms[4:6]),
                tzinfo=_KST,
            )
        except ValueError:
            continue
        ts_utc = int(dt_kst.astimezone(timezone.utc).timestamp())
        # lightweight-charts는 유닉스 타임스탬프를 UTC로 표시하므로, KST 벽시계가
        # 그대로 보이도록 +9h 보정한다(한국 주식 차트 축은 KST 기준).
        candles.append({"time": ts_utc + _KST_OFFSET_SEC, **body})
    candles.sort(key=lambda c: c["time"])
    return candles


async def _get_period_chart(
    symbol: str,
    period_div_code: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    today = datetime.now(_KST).date()
    start = today - timedelta(days=_LOOKBACK_DAYS)
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
        "FID_INPUT_DATE_2": today.strftime("%Y%m%d"),
        "FID_PERIOD_DIV_CODE": period_div_code,
        "FID_ORG_ADJ_PRC": "1",
    }
    try:
        data = await client.get(_CHART_PATH, QUOTE_TR_IDS["inquire_daily_itemchartprice"], params)
    except httpx.HTTPError as exc:
        logger.warning("차트 HTTP 호출 실패 %s/%s: %s", symbol, period_div_code, exc)
        raise ChartUnavailableError(f"차트 조회 실패: {symbol}") from exc

    if data.get("rt_cd") != "0":
        logger.warning(
            "차트 조회 응답 오류 %s/%s: %s(%s)",
            symbol,
            period_div_code,
            data.get("msg1"),
            data.get("msg_cd"),
        )
        raise ChartUnavailableError(data.get("msg1") or f"차트 조회 오류: {symbol}")

    output2 = data.get("output2") or []
    if not output2:
        logger.info("차트 데이터 없음 %s/%s: %s", symbol, period_div_code, data.get("msg1"))

    candles = _parse_period_rows(output2)
    if output2 and not candles:
        logger.warning("차트 파싱 실패 %s/%s", symbol, period_div_code)
    return candles


async def get_daily_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    return await _get_period_chart(symbol, "D", settings=settings, kis_client=kis_client)


async def get_weekly_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    return await _get_period_chart(symbol, "W", settings=settings, kis_client=kis_client)


async def get_minute_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    # KIS 분봉은 '지정 시각 기준 직전 30분'을 반환한다. 장 마감(15:30) 이후나 개장 전에
    # 현재 시각으로 조회하면 장외 평탄 구간만 잡히므로, 정규장 밖이면 마감 시각으로 고정해
    # 마지막 거래 세션의 실제 분봉을 가져온다.
    now_kst = datetime.now(_KST)
    minutes = now_kst.hour * 60 + now_kst.minute
    if _MARKET_OPEN_MIN <= minutes <= _MARKET_CLOSE_MIN:
        hour_1 = now_kst.strftime("%H%M%S")
    else:
        hour_1 = _MARKET_CLOSE_HMS
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_HOUR_1": hour_1,
        "FID_PW_DATA_INCU_YN": "Y",
        "FID_ETC_CLS_CODE": "",
    }
    try:
        data = await client.get(_MINUTE_PATH, QUOTE_TR_IDS["inquire_time_itemchartprice"], params)
    except httpx.HTTPError as exc:
        logger.warning("분봉 HTTP 호출 실패 %s: %s", symbol, exc)
        raise ChartUnavailableError(f"분봉 조회 실패: {symbol}") from exc

    if data.get("rt_cd") != "0":
        logger.warning(
            "분봉 조회 응답 오류 %s: %s(%s)",
            symbol,
            data.get("msg1"),
            data.get("msg_cd"),
        )
        raise ChartUnavailableError(data.get("msg1") or f"분봉 조회 오류: {symbol}")

    output2 = data.get("output2") or []
    if not output2:
        logger.info("분봉 데이터 없음 %s: %s", symbol, data.get("msg1"))

    candles = _parse_minute_rows(output2)
    if output2 and not candles:
        logger.warning("분봉 파싱 실패 %s", symbol)
    return candles
