"""KIS 종목 차트(일봉/분봉) 조회."""

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
    """KIS 일시 오류로 차트를 조회하지 못함.

    '진짜 데이터 없음'(빈 캔들)과 구분하기 위한 예외다. 재시도로 회복 가능한
    상황(레이트리밋·토큰 만료·일시 5xx)을 호출 측이 오류로 인지하게 한다.
    """


_DAILY_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
_MINUTE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice"

_KST = timezone(timedelta(hours=9))
_DAILY_LOOKBACK_DAYS = 200


def _ohlcv(oprc: Any, hgpr: Any, lwpr: Any, close: Any, vol: Any) -> dict[str, Any] | None:
    """OHLCV를 int로 변환한다. 종가가 있으면 나머지는 0으로라도 채운다."""
    c = to_int(close)
    if c is None:
        return None
    o = to_int(oprc) or c
    h = to_int(hgpr) or c
    low = to_int(lwpr) or c
    v = to_int(vol) or 0
    return {"open": o, "high": h, "low": low, "close": c, "volume": v}


def _parse_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _parse_minute(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for r in rows:
        date = (r.get("stck_bsop_date") or "").strip()
        hms = (r.get("stck_cntg_hour") or "").strip()
        if len(date) != 8 or len(hms) < 4:  # HHMMSS 또는 HHMM
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
            candles.append({"time": int(dt_kst.astimezone(timezone.utc).timestamp()), **body})
        except ValueError:
            continue
    candles.sort(key=lambda c: c["time"])
    return candles


async def get_daily_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """일봉 차트(최근 약 100영업일)를 반환한다.

    KIS 일시 오류(httpx 오류·rt_cd≠0)는 빈 리스트가 아니라 ``ChartUnavailableError``로
    전파한다. 빈 리스트는 '정상 응답이나 데이터 없음'만을 의미한다.
    """
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
        logger.warning("일봉 HTTP 호출 실패 %s: %s", symbol, exc)
        raise ChartUnavailableError(f"일봉 조회 실패: {symbol}") from exc

    if data.get("rt_cd") != "0":
        logger.warning(
            "일봉 조회 응답 오류 %s: %s(%s)",
            symbol,
            data.get("msg1"),
            data.get("msg_cd"),
        )
        raise ChartUnavailableError(data.get("msg1") or f"일봉 조회 오류: {symbol}")

    output2 = data.get("output2") or []
    if not output2:
        logger.info("일봉 데이터 없음 %s: %s", symbol, data.get("msg1"))

    candles = _parse_daily(output2)
    if output2 and not candles:
        logger.warning("일봉 데이터 파싱 실패 %s (데이터는 있으나 유효한 캔들 없음)", symbol)
    return candles


async def get_minute_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """분봉 차트를 반환한다.

    KIS 일시 오류(httpx 오류·rt_cd≠0)는 빈 리스트가 아니라 ``ChartUnavailableError``로
    전파한다. 빈 리스트는 '정상 응답이나 데이터 없음'(장 마감 후·주말 등)만을 의미한다.
    """
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    # FID_INPUT_HOUR_1을 현재 시각으로 보내거나, 빈 값으로 보내 최신 데이터를 가져온다.
    # 일부 종목은 현재 시각을 보내면 결과가 비어있는 경우가 있어 빈 값 시도 고려 가능.
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

    candles = _parse_minute(output2)
    if output2 and not candles:
        logger.warning("분봉 데이터 파싱 실패 %s (데이터는 있으나 유효한 캔들 없음)", symbol)
    return candles
