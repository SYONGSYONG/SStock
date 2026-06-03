"""기업개요 라우터.

GET /api/company/{symbol}/overview — 네이버금융(WiseReport) 기업개요 스크래핑.
스크래핑 실패·구조 변경 시에도 빈 개요로 graceful 응답. 설계: docs/09-company-overview.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.stocks.naver import get_company_overview

router = APIRouter(prefix="/api/company", tags=["company"])


@router.get("/{symbol}/overview")
async def company_overview(symbol: str) -> dict:
    data = await get_company_overview(symbol)
    return {"data": data}
