"""KIS 시세 조회 서비스."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import QUOTE_TR_IDS
from app.kis.numbers import to_float as _to_float
from app.kis.numbers import to_int as _to_int

logger = logging.getLogger(__name__)

_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"

_EMPTY_FIELDS = ("price", "change", "change_rate", "sign", "volume", "open", "high", "low")


def _empty_quote(symbol: str) -> dict[str, Any]:
    return {"symbol": symbol, **{k: None for k in _EMPTY_FIELDS}}


async def get_current_price(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> dict[str, Any]:
    """주식 현재가 시세를 조회한다 (FHKST01010100).

    KIS가 일시적으로 실패(예: 초당 거래건수 제한, 특정 종목 5xx)해도 예외를
    전파하지 않고 값이 비어 있는 시세를 반환한다(대시보드는 '-'로 표시).
    """
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    try:
        data = await client.get(
            _PRICE_PATH,
            QUOTE_TR_IDS["inquire_price"],
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
    except httpx.HTTPError as exc:
        logger.warning("시세 조회 실패 %s: %s", symbol, exc)
        return _empty_quote(symbol)

    out = data.get("output") or {}
    return {
        "symbol": symbol,
        "price": _to_int(out.get("stck_prpr")),
        "change": _to_int(out.get("prdy_vrss")),
        "change_rate": _to_float(out.get("prdy_ctrt")),
        "sign": out.get("prdy_vrss_sign"),
        "volume": _to_int(out.get("acml_vol")),
        "open": _to_int(out.get("stck_oprc")),
        "high": _to_int(out.get("stck_hgpr")),
        "low": _to_int(out.get("stck_lwpr")),
    }
