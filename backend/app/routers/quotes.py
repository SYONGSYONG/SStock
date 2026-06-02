"""시세 조회 라우터."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.kis.quotes import get_current_price

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


def _validate_symbol(symbol: str) -> None:
    if not (len(symbol) == 6 and symbol.isdigit()):
        raise HTTPException(
            status_code=400,
            detail={"error": "종목코드는 6자리 숫자여야 합니다", "code": "INVALID_SYMBOL"},
        )


@router.get("/{symbol}")
async def current_price(symbol: str) -> dict:
    _validate_symbol(symbol)
    data = await get_current_price(symbol)
    return {"data": data}
