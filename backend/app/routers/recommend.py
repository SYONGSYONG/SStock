"""분야별 추천 종목 라우터.

GET /api/recommend/themes        — 테마 목록 + 종목 수 (로컬 .mst, API 호출 없음)
GET /api/recommend/{theme}       — 해당 테마 추천 종목 (하이브리드 파이프라인)
GET /api/recommend/{theme}/stream — 해당 테마 추천 종목 (SSE 스트리밍)

설계: docs/06-recommend.md.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.kis.quotes import get_current_price
from app.kis.rankings import get_investor_flow, get_investor_flow_daily
from app.services import recommend_service
from app.stocks import krx, sector

router = APIRouter(prefix="/api/recommend", tags=["recommend"])


async def _resolve_fns(
    settings,
) -> tuple[recommend_service.PriceFn, recommend_service.FlowFn]:
    """추천 시세 데이터 소스에 따라 price_fn과 flow_fn을 결정한다.

    - source == "krx": KRX 스냅샷 기반 price_fn + KIS 일별 캐시 수급 flow_fn
    - source == "kis" (기본): KIS 현재가 + 수급 fn
    """
    if settings.recommend_data_source == "krx":
        # KRX 스냅샷 1회 조회 (lazy: price_fn 첫 호출 시)
        snapshot: dict[str, dict[str, Any]] | None = None

        async def krx_price_fn(symbol: str) -> dict[str, Any]:
            nonlocal snapshot
            if snapshot is None:
                # 첫 호출: 스냅샷 조회 (캐시/단일비행으로 1회만 네트워크)
                snapshot = await krx.get_market_snapshot(settings)
            data = snapshot.get(symbol, {})
            return {
                "symbol": symbol,
                "price": data.get("price"),
                "change_rate": data.get("change_rate"),
                "volume": data.get("volume"),
            }

        # 수급은 KRX 미제공 → KIS로 조회하되 종목별 하루 캐시(EOD라 종목당 1회).
        return krx_price_fn, get_investor_flow_daily
    else:
        # KIS (기본값)
        return get_current_price, get_investor_flow


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
    settings = get_settings()
    price_fn, flow_fn = await _resolve_fns(settings)
    result = await recommend_service.recommend_for_theme(
        theme,
        limit,
        price_fn=price_fn,
        flow_fn=flow_fn,
    )
    if settings.recommend_data_source == "krx":
        # KRX는 EOD라 시세 기준일(거래일)을 재무 기준일과 구분해 노출한다.
        result = {**result, "price_date": krx.get_resolved_date()}
    return {"data": result}


@router.get("/{theme}/stream")
async def recommend_stream(
    theme: str,
    limit: int = Query(default=recommend_service.DEFAULT_RESULT_LIMIT, ge=1, le=30),
):
    """SSE 스트리밍 추천 엔드포인트.

    이벤트 시퀀스:
    1. "candidates" — 후보 목록 + 기준일 (즉시)
    2. "quote"* — 종목별 시세 (완료 순서대로)
    3. "result" — 최종 점수 + 정렬된 종목 (또는 캐시 히트 시 바로)
    에러 시: "error" — 오류 메시지

    KRX 모드에서는 candidates 즉시 후 스냅샷을 lazy 조회하므로,
    candidates 출력이 지연되지 않는다.
    """
    if theme not in sector.THEMES:
        raise HTTPException(
            status_code=404,
            detail={"error": "알 수 없는 테마입니다", "code": "UNKNOWN_THEME"},
        )

    async def event_generator():
        try:
            settings = get_settings()
            price_fn, flow_fn = await _resolve_fns(settings)
            async for event, payload in recommend_service.stream_recommend_for_theme(
                theme,
                limit,
                price_fn=price_fn,
                flow_fn=flow_fn,
            ):
                if event == "result" and settings.recommend_data_source == "krx":
                    # KRX 시세 기준일(거래일)을 result에 덧붙인다.
                    payload = {**payload, "price_date": krx.get_resolved_date()}
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': 'RECOMMEND_STREAM_ERROR'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
