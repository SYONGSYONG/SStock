"""계좌 잔고 조회 라우터.

KIS 주식잔고조회(output2) 기반 예수금/주문가능/총평가/평가손익/순자산 요약.
KIS 일시 장애 시에도 대시보드가 500으로 깨지지 않도록 빈 요약으로 graceful 처리한다.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.kis.orders import get_account_summary

router = APIRouter(prefix="/api/account", tags=["account"])

logger = logging.getLogger(__name__)

_EMPTY_SUMMARY: dict[str, int | None] = {
    "deposit": None,
    "orderable_cash": None,
    "purchase_amount": None,
    "eval_amount": None,
    "eval_pnl": None,
    "total_eval": None,
    "net_asset": None,
}


@router.get("/balance")
async def balance(settings: Settings = Depends(get_settings)) -> dict:
    """계좌 잔고 요약. KIS 오류 시 모든 값 None(조회 불가)으로 반환한다."""
    try:
        summary = await get_account_summary(settings)
        return {"data": {"mode": settings.trading_mode, "available": True, **summary}}
    except httpx.HTTPError as exc:
        logger.warning("계좌 잔고 조회 실패: %s", exc)
        return {"data": {"mode": settings.trading_mode, "available": False, **_EMPTY_SUMMARY}}
