"""분야별 추천 종목 라우터.

GET /api/recommend/themes        — 테마 목록 + 종목 수 (로컬 .mst, API 호출 없음)
GET /api/recommend/{theme}       — 해당 테마 추천 종목 (하이브리드 파이프라인)
GET /api/recommend/{theme}/stream — 해당 테마 추천 종목 (SSE 스트리밍)

설계: docs/06-recommend.md.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

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


@router.get("/{theme}/stream")
async def recommend_stream(
    theme: str,
    limit: int = Query(default=recommend_service.DEFAULT_RESULT_LIMIT, ge=1, le=30),
):
    """SSE 스트리밍 추천 엔드포인트.

    이벤트 시퀀스:
    1. "candidates" — 후보 목록 + 기준일
    2. "quote"* — 종목별 시세 (완료 순서대로)
    3. "result" — 최종 점수 + 정렬된 종목 (또는 캐시 히트 시 바로)
    에러 시: "error" — 오류 메시지
    """
    if theme not in sector.THEMES:
        raise HTTPException(
            status_code=404,
            detail={"error": "알 수 없는 테마입니다", "code": "UNKNOWN_THEME"},
        )

    async def event_generator():
        try:
            async for event, payload in recommend_service.stream_recommend_for_theme(
                theme,
                limit,
                price_fn=get_current_price,
                flow_fn=get_investor_flow,
            ):
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': 'RECOMMEND_STREAM_ERROR'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
