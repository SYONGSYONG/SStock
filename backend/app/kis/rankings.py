"""KIS 수급(투자자별 순매수) 조회.

추천 복합 점수의 **수급 축**(외국인·기관 순매수)에 쓰인다. 종목별로
주식현재가 투자자(inquire-investor, FHKST01010900)를 호출해 최신 영업일
기준 외국인/기관 순매수 수량을 가져온다.

시세 조회와 동일하게, KIS 일시 실패 시 예외를 전파하지 않고 값이 비어 있는
결과(None)를 반환한다(추천 점수는 중립으로 degrade).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import QUOTE_TR_IDS
from app.kis.numbers import to_int

logger = logging.getLogger(__name__)

_INVESTOR_PATH = "/uapi/domestic-stock/v1/quotations/inquire-investor"


def _empty_flow(symbol: str) -> dict[str, Any]:
    return {"symbol": symbol, "foreign_net": None, "inst_net": None}


async def get_investor_flow(
    symbol: str,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> dict[str, Any]:
    """종목의 외국인·기관 순매수 수량(최신 영업일)을 조회한다."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
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
