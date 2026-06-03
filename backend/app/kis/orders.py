"""KIS 주문/잔고 API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import Settings, get_settings
from app.kis.client import KisClient
from app.kis.constants import resolve_tr_id
from app.kis.numbers import to_float, to_int

_ORDER_PATH = "/uapi/domestic-stock/v1/trading/order-cash"
_RVSECNCL_PATH = "/uapi/domestic-stock/v1/trading/order-rvsecncl"
_BALANCE_PATH = "/uapi/domestic-stock/v1/trading/inquire-balance"
_DAILY_CCLD_PATH = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"


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
    """주식 주문(현금). price가 있으면 지정가(00), 없으면 시장가(01)."""
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
    """주문 취소(order-rvsecncl, RVSE_CNCL_DVSN_CD=02)."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    tr_id = resolve_tr_id("order_rvsecncl", settings.trading_mode)
    body = {
        "CANO": settings.kis_account_no,
        "ACNT_PRDT_CD": settings.kis_account_product,
        "KRX_FWDG_ORD_ORGNO": branch_no,
        "ORGN_ODNO": org_order_no,
        "ORD_DVSN": "00",
        "RVSE_CNCL_DVSN_CD": "02",
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
    """주식 잔고조회. 보유 종목 리스트(수량>0)를 반환한다."""
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


def _first_summary(output2: Any) -> dict[str, Any]:
    """inquire-balance output2(계좌 요약)에서 첫 원소를 dict로 반환한다."""
    if isinstance(output2, list):
        return output2[0] if output2 else {}
    if isinstance(output2, dict):
        return output2
    return {}


async def get_account_summary(
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> dict[str, Any]:
    """주식 잔고조회 output2 기준 계좌 요약을 반환한다."""
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
    s = _first_summary(data.get("output2"))
    return {
        "deposit": to_int(s.get("dnca_tot_amt")),
        "orderable_cash": to_int(s.get("prvs_rcdl_excc_amt")),
        "purchase_amount": to_int(s.get("pchs_amt_smtl_amt")),
        "eval_amount": to_int(s.get("evlu_amt_smtl_amt")),
        "eval_pnl": to_int(s.get("evlu_pfls_smtl_amt")),
        "total_eval": to_int(s.get("tot_evlu_amt")),
        "net_asset": to_int(s.get("nass_amt")),
    }


def _kst_today() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")


async def get_daily_ccld(
    order_no: str,
    symbol: str | None = None,
    settings: Settings | None = None,
    kis_client: KisClient | None = None,
) -> list[dict[str, Any]]:
    """당일 주문체결내역을 조회한다."""
    settings = settings or get_settings()
    client = kis_client or KisClient(settings)
    tr_id = resolve_tr_id("inquire_daily_ccld", settings.trading_mode)
    today = _kst_today()
    params = {
        "CANO": settings.kis_account_no,
        "ACNT_PRDT_CD": settings.kis_account_product,
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",
        "PDNO": symbol or "",
        "CCLD_DVSN": "00",
        "INQR_DVSN": "00",
        "INQR_DVSN_3": "00",
        "ORD_GNO_BRNO": "",
        "ODNO": order_no,
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
        "EXCG_ID_DVSN_CD": "KRX",
    }
    data = await client.get(_DAILY_CCLD_PATH, tr_id, params)
    rows = data.get("output1") or []
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "ord_dt": row.get("ord_dt"),
                "ord_gno_brno": row.get("ord_gno_brno"),
                "odno": row.get("odno"),
                "orgn_odno": row.get("orgn_odno"),
                "pdno": row.get("pdno"),
                "prdt_name": row.get("prdt_name"),
                "ord_qty": to_int(row.get("ord_qty")) or 0,
                "tot_ccld_qty": to_int(row.get("tot_ccld_qty")) or 0,
                "rmn_qty": to_int(row.get("rmn_qty")) or 0,
                "ord_unpr": to_float(row.get("ord_unpr")),
                "cncl_yn": str(row.get("cncl_yn") or ""),
                "rjct_qty": to_int(row.get("rjct_qty")) or 0,
                "ccld_cndt_name": row.get("ccld_cndt_name"),
            }
        )
    return result
