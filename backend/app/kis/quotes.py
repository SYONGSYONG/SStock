"""KIS 시세 조회 서비스."""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import QUOTE_TR_IDS
from app.kis.numbers import to_float as _to_float
from app.kis.numbers import to_int as _to_int

_PRICE_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"


async def get_current_price(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> dict[str, Any]:
    """주식 현재가 시세를 조회한다 (FHKST01010100)."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    data = await client.get(
        _PRICE_PATH,
        QUOTE_TR_IDS["inquire_price"],
        {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
    )
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
