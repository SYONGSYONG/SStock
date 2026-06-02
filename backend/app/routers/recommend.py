"""분야별 추천 종목 라우터.

GET /api/recommend/themes        — 테마 목록 + 종목 수 (로컬 .mst, API 호출 없음)
GET /api/recommend/{theme}       — 해당 테마 추천 종목 (하이브리드 파이프라인)

설계: docs/06-recommend.md.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.kis.quotes import get_current_price
from app.kis.rankings import get_investor_flow
from app.services import recommend_service
from app.stocks import sector

router = APIRouter(prefix="/api/recommend", tags=["recommend"])


@router.get("/themes")
def list_themes() -> dict:
    return {"data": sector.list_themes()}


@router.get("/{theme}")
async def recommend(
    theme: str,
    limit: int = Query(default=recommend_service.DEFAULT_RESULT_LIMIT, ge=1, le=30),
) -> dict:
    if theme not in sector.THEMES:
        raise HTTPException(
            status_code=404,
            detail={"error": "알 수 없는 테마입니다", "code": "UNKNOWN_THEME"},
        )
    result = await recommend_service.recommend_for_theme(
        theme,
        limit,
        price_fn=get_current_price,
        flow_fn=get_investor_flow,
    )
    return {"data": result}
