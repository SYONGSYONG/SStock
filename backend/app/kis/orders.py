"""KIS 주문/잔고 API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import resolve_tr_id
from app.kis.numbers import to_float, to_int

_ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"
_RVSECNCL_PATH = "/uapi/domestic-stock/v1/trading/order-rvsecncl"
_BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"


@dataclass(frozen=True)
class OrderResult:
    ok: bool
    kis_order_no: str | None
    message: str | None


async def place_order(
    symbol: str,
    side: str,
    qty: int,
    price: float | None,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> OrderResult:
    """주식주문(현금). price가 있으면 지정가(00), 없으면 시장가(01)."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    tr_key = "order_cash_buy" if side == "BUY" else "order_cash_sell"
    tr_id = resolve_tr_id(tr_key, settings.trading_mode)
    body = {
        "CANO": settings.kis_account_no,
        "ACNT_PRDT_CD": settings.kis_account_product,
        "PDNO": symbol,
        "ORD_DVSN": "00" if price else "01",
        "ORD_QTY": str(qty),
        "ORD_UNPR": str(int(price)) if price else "0",
    }
    data = await client.post(_ORDER_PATH, tr_id, body)
    out = data.get("output") or {}
    return OrderResult(
        ok=data.get("rt_cd") == "0",
        kis_order_no=out.get("ODNO"),
        message=data.get("msg1"),
    )


async def cancel_order(
    symbol: str,
    org_order_no: str,
    qty: int,
    branch_no: str = "",
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> OrderResult:
    """주문 취소 (order-rvsecncl, RVSE_CNCL_DVSN_CD=02)."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    tr_id = resolve_tr_id("order_rvsecncl", settings.trading_mode)
    body = {
        "CANO": settings.kis_account_no,
        "ACNT_PRDT_CD": settings.kis_account_product,
        "KRX_FWDG_ORD_ORGNO": branch_no,
        "ORGN_ODNO": org_order_no,
        "ORD_DVSN": "00",
        "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
        "ORD_QTY": str(qty),
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y",
    }
    data = await client.post(_RVSECNCL_PATH, tr_id, body)
    out = data.get("output") or {}
    return OrderResult(
        ok=data.get("rt_cd") == "0",
        kis_order_no=out.get("ODNO"),
        message=data.get("msg1"),
    )


async def get_balance(
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """주식잔고조회. 보유 종목 리스트(수량>0)를 반환한다."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    tr_id = resolve_tr_id("inquire_balance", settings.trading_mode)
    params = {
        "CANO": settings.kis_account_no,
        "ACNT_PRDT_CD": settings.kis_account_product,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    data = await client.get(_BALANCE_PATH, tr_id, params)
    holdings = data.get("output1") or []
    result: list[dict[str, Any]] = []
    for h in holdings:
        qty = to_int(h.get("hldg_qty")) or 0
        if qty <= 0:
            continue
        result.append(
            {
                "symbol": h.get("pdno"),
                "name": h.get("prdt_name"),
                "qty": qty,
                "avg_price": to_float(h.get("pchs_avg_pric")),
                "price": to_int(h.get("prpr")),
                "eval_amount": to_int(h.get("evlu_amt")),
                "pl_amount": to_int(h.get("evlu_pfls_amt")),
                "pl_rate": to_float(h.get("evlu_pfls_rt")),
            }
        )
    return result
