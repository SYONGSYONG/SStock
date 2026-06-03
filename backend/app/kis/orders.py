"""KIS 주문/잔고 API."""

from __future__ import annotations

import asyncio
import time
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

# inquire-balance 응답에는 보유종목(output1)과 계좌요약(output2)이 함께 온다.
# 잔고 요약(get_account_summary)과 포지션(get_balance)이 같은 호출을 공유하도록
# 원시 응답을 짧은 TTL + 단일비행으로 캐시한다. 대시보드 5초 폴링이 같은 데이터를
# KIS에 2번 부르던 것을 1번으로 줄여, 차트 등 사용자 조회와의 레이트리밋 경합을 낮춘다.
_BALANCE_TTL_SEC = 2.0
_balance_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_balance_locks: dict[str, asyncio.Lock] = {}


class AccountUnavailableError(RuntimeError):
    """잔고 조회가 KIS 오류(rt_cd≠0, 예: 잘못된 계좌)로 실패했을 때 발생.

    HTTP 200이라도 rt_cd≠0이면 값이 비어 오므로, 침묵 실패(빈 값 표시)를 막기 위해
    예외로 구분한다. 라우터가 이를 잡아 '조회 불가'(available=false)로 응답한다.
    """


def clear_balance_cache() -> None:
    """잔고 원시 응답 캐시를 비운다(테스트·강제 갱신용)."""
    _balance_cache.clear()
    _balance_locks.clear()


def _balance_params(settings: Settings, mode: str | None = None) -> dict[str, str]:
    """모드별 잔고조회 파라미터를 반환한다."""
    mode_resolved = mode or settings.trading_mode
    creds = settings.kis_for(mode_resolved)
    return {
        "CANO": creds.account_no,
        "ACNT_PRDT_CD": creds.account_product,
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


async def _get_balance_raw(
    settings: Settings,
    kis_client: KisClient | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """inquire-balance 원시 응답(짧은 TTL + 단일비행 캐시). 정상 응답만 캐시한다.

    모드별로 계좌번호가 다르므로 캐시 키도 모드별로 분리한다.
    """
    mode_resolved = mode or settings.trading_mode
    creds = settings.kis_for(mode_resolved)
    key = f"{creds.account_no}:{mode_resolved}"
    cached = _balance_cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < _BALANCE_TTL_SEC:
        return cached[1]
    lock = _balance_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _balance_cache.get(key)
        if cached is not None and time.monotonic() - cached[0] < _BALANCE_TTL_SEC:
            return cached[1]
        client = kis_client or KisClient(settings, mode=mode_resolved)
        tr_id = resolve_tr_id("inquire_balance", mode_resolved)
        data = await client.get(_BALANCE_PATH, tr_id, _balance_params(settings, mode_resolved))
        # rt_cd≠0(예: INVALID_CHECK_ACNO)이면 값이 비어 오므로 침묵 실패로 두지 않고
        # 예외로 구분한다(캐시도 안 함 → 다음 호출에서 재시도).
        if data.get("rt_cd") != "0":
            raise AccountUnavailableError(data.get("msg1") or "잔고 조회 실패")
        _balance_cache[key] = (time.monotonic(), data)
        return data


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
    mode: str | None = None,
) -> OrderResult:
    """주식 주문(현금). price가 있으면 지정가(00), 없으면 시장가(01).

    mode: 모드(paper/live). 미지정 시 settings.trading_mode.
    """
    settings = settings or get_settings()
    mode_resolved = mode or settings.trading_mode
    creds = settings.kis_for(mode_resolved)
    client = kis_client or KisClient(settings, mode=mode_resolved)
    tr_key = "order_cash_buy" if side == "BUY" else "order_cash_sell"
    tr_id = resolve_tr_id(tr_key, mode_resolved)
    body = {
        "CANO": creds.account_no,
        "ACNT_PRDT_CD": creds.account_product,
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
    mode: str | None = None,
) -> OrderResult:
    """주문 취소(order-rvsecncl, RVSE_CNCL_DVSN_CD=02).

    mode: 모드(paper/live). 미지정 시 settings.trading_mode.
    """
    settings = settings or get_settings()
    mode_resolved = mode or settings.trading_mode
    creds = settings.kis_for(mode_resolved)
    client = kis_client or KisClient(settings, mode=mode_resolved)
    tr_id = resolve_tr_id("order_rvsecncl", mode_resolved)
    body = {
        "CANO": creds.account_no,
        "ACNT_PRDT_CD": creds.account_product,
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
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """주식 잔고조회. 보유 종목 리스트(수량>0)를 반환한다.

    mode: 모드(paper/live). 미지정 시 settings.trading_mode.
    """
    settings = settings or get_settings()
    data = await _get_balance_raw(settings, kis_client, mode=mode)
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
    mode: str | None = None,
) -> dict[str, Any]:
    """주식 잔고조회 output2 기준 계좌 요약을 반환한다.

    mode: 모드(paper/live). 미지정 시 settings.trading_mode.
    """
    settings = settings or get_settings()
    data = await _get_balance_raw(settings, kis_client, mode=mode)
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
    mode: str | None = None,
) -> list[dict[str, Any]]:
    """당일 주문체결내역을 조회한다.

    mode: 모드(paper/live). 미지정 시 settings.trading_mode.
    """
    settings = settings or get_settings()
    mode_resolved = mode or settings.trading_mode
    creds = settings.kis_for(mode_resolved)
    client = kis_client or KisClient(settings, mode=mode_resolved)
    tr_id = resolve_tr_id("inquire_daily_ccld", mode_resolved)
    today = _kst_today()
    params = {
        "CANO": creds.account_no,
        "ACNT_PRDT_CD": creds.account_product,
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
