"""KIS 수급(투자자별 순매수) 조회.

추천 복합 점수의 **수급 축**(외국인·기관 순매수)에 쓰인다. 종목별로
주식현재가 투자자(inquire-investor, FHKST01010900)를 호출해 최신 영업일
기준 외국인/기관 순매수 수량을 가져온다.

시세 조회와 동일하게, KIS 일시 실패 시 예외를 전파하지 않고 값이 비어 있는
결과(None)를 반환한다(추천 점수는 중립으로 degrade).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import QUOTE_TR_IDS
from app.kis.numbers import to_int

logger = logging.getLogger(__name__)

_INVESTOR_PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor"

# 수급은 장 종료 후 1회 정산(EOD)이라 종목별 하루 캐시로 호출을 절약한다.
# KRX 시세 전환 후에도 수급만 KIS로 받으므로, 종목당 하루 1회 호출이 되게 한다.
_FLOW_TTL_SEC = 86400.0  # 하루
_flow_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_flow_locks: dict[str, asyncio.Lock] = {}


def clear_flow_cache() -> None:
    """수급 캐시를 비운다(테스트·강제 갱신용)."""
    _flow_cache.clear()
    _flow_locks.clear()


def _empty_flow(symbol: str) -> dict[str, Any]:
    return {"symbol": symbol, "foreign_net": None, "inst_net": None}


async def get_investor_flow(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """종목의 외국인·기관 순매수 수량(최신 영업일)을 조회한다.

    mode: KIS 호출에 쓸 모드(레이트리밋용). 수급은 읽기 전용 시세라 모드 무관 동일 데이터.
    """
    settings = settings or get_settings()
    client = kis_client or KisClient(settings, mode=mode)
    try:
        data = await client.get(
            _INVESTOR_PATH,
            QUOTE_TR_IDS["inquire_investor"],
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
    except httpx.HTTPError as exc:
        logger.warning("수급 조회 실패 %s: %s", symbol, exc)
        return _empty_flow(symbol)

    out = data.get("output")
    if isinstance(out, list):
        row = out[0] if out else {}
    elif isinstance(out, dict):
        row = out
    else:
        row = {}

    return {
        "symbol": symbol,
        "foreign_net": to_int(row.get("frgn_ntby_qty")),
        "inst_net": to_int(row.get("orgn_ntby_qty")),
    }


async def get_investor_flow_daily(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """종목별 하루 캐시를 적용한 수급 조회.

    수급은 EOD 정산이라 종목당 하루 1회만 KIS를 호출하면 충분하다.
    종목별 단일비행(Lock)으로 동시 호출도 1회로 직렬화한다.
    오류(빈 수급=None)는 캐시하지 않아 다음 호출에서 재시도한다.
    """
    cached = _flow_cache.get(symbol)
    if cached is not None and time.monotonic() - cached[0] < _FLOW_TTL_SEC:
        return cached[1]

    lock = _flow_locks.setdefault(symbol, asyncio.Lock())
    async with lock:
        cached = _flow_cache.get(symbol)
        if cached is not None and time.monotonic() - cached[0] < _FLOW_TTL_SEC:
            return cached[1]
        flow = await get_investor_flow(symbol, settings, kis_client, mode=mode)
        # 유효한 수급만 캐시(오류로 인한 None은 캐시하지 않음)
        if flow.get("foreign_net") is not None or flow.get("inst_net") is not None:
            _flow_cache[symbol] = (time.monotonic(), flow)
        return flow
