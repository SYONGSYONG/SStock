"""KIS 종목 차트(일봉/주봉/분봉) 조회."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
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
# KIS inquire-daily-itemchartprice는 1회 응답 최대 100건. 봉별로 lookback을 분리해
# 100건 상한을 채운다(같은 1회 호출이라 건수가 늘어도 속도 영향은 사실상 없음).
_LOOKBACK_DAYS = 200  # 일봉: ~200일 ≈ 100영업일
_WEEKLY_LOOKBACK_DAYS = 730  # 주봉: ~2년 ≈ 100주

# 국내 정규장: 09:00 ~ 15:30 (KST)
_MARKET_OPEN_MIN = 9 * 60
_MARKET_CLOSE_MIN = 15 * 60 + 30
_MARKET_CLOSE_HMS = "153000"

# 차트 캐시: 모달을 다시 열거나 탭을 전환할 때마다 KIS를 재호출하지 않도록
# (symbol, interval)별로 캔들을 캐시한다. 일/주봉은 장중 마지막 봉만 갱신되고
# 장외에는 고정이므로 TTL을 시장 시간대에 맞춰 조절한다. 분봉은 더 짧게 둔다.
# 빈 결과/오류는 캐시하지 않아(아래 _cached_fetch) 다음 호출에서 재시도한다.
_chart_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_chart_locks: dict[str, asyncio.Lock] = {}

_TTL_PERIOD_MARKET = 60.0  # 일/주봉 장중: 1분(마지막 봉 갱신 반영)
_TTL_MINUTE_MARKET = 30.0  # 분봉 장중: 30초
_TTL_CLOSED = 1800.0  # 장외(데이터 고정): 30분


def clear_chart_cache() -> None:
    """차트 캐시를 비운다(테스트·강제 갱신용)."""
    _chart_cache.clear()
    _chart_locks.clear()


def _is_market_hours() -> bool:
    """현재가 국내 정규장(평일 09:00~15:30 KST)인지 여부."""
    now = datetime.now(_KST)
    if now.weekday() >= 5:  # 토(5)·일(6)
        return False
    minutes = now.hour * 60 + now.minute
    return _MARKET_OPEN_MIN <= minutes <= _MARKET_CLOSE_MIN


async def _cached_fetch(
    key: str, ttl: float, fetcher: Callable[[], Awaitable[list[dict[str, Any]]]]
) -> list[dict[str, Any]]:
    """(symbol,interval) 키로 캔들을 캐시한다. 단일비행(Lock)으로 동시 호출을 1회로 묶고,
    빈 결과/오류는 캐시하지 않는다(예외는 그대로 전파)."""
    cached = _chart_cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < ttl:
        return cached[1]
    lock = _chart_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _chart_cache.get(key)
        if cached is not None and time.monotonic() - cached[0] < ttl:
            return cached[1]
        candles = await fetcher()
        if candles:  # 빈 결과는 캐시하지 않음(재시도 여지)
            _chart_cache[key] = (time.monotonic(), candles)
        return candles


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
    lookback = _WEEKLY_LOOKBACK_DAYS if period_div_code == "W" else _LOOKBACK_DAYS
    start = today - timedelta(days=lookback)
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
    ttl = _TTL_PERIOD_MARKET if _is_market_hours() else _TTL_CLOSED
    return await _cached_fetch(
        f"{symbol}:D", ttl, lambda: _get_period_chart(symbol, "D", settings, kis_client)
    )


async def get_weekly_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    ttl = _TTL_PERIOD_MARKET if _is_market_hours() else _TTL_CLOSED
    return await _cached_fetch(
        f"{symbol}:W", ttl, lambda: _get_period_chart(symbol, "W", settings, kis_client)
    )


async def get_minute_chart(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    ttl = _TTL_MINUTE_MARKET if _is_market_hours() else _TTL_CLOSED
    return await _cached_fetch(
        f"{symbol}:m", ttl, lambda: _fetch_minute_chart(symbol, settings, kis_client)
    )


async def _fetch_minute_chart(
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
