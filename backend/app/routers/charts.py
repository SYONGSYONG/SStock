"""종목 차트(일봉/주봉/분봉) 라우터."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.kis.charts import ChartUnavailableError, get_daily_chart, get_minute_chart, get_weekly_chart

router = APIRouter(prefix="/api/charts", tags=["charts"])

_INTERVALS = ("daily", "weekly", "minute")
_MINUTE_UNITS = (1, 5, 10, 30)


@router.get("/{symbol}")
async def chart(
    symbol: str,
    interval: str = Query(default="daily"),
    unit: int = Query(default=1, description="분봉 단위(분): 1·5·10·30"),
    scope: str = Query(default="session", description='분봉 데이터 출처: "today" 또는 "session"'),
) -> dict:
    if interval not in _INTERVALS:
        raise HTTPException(
            status_code=400,
            detail={"error": "interval은 daily, weekly 또는 minute 이어야 합니다", "code": "BAD_INTERVAL"},
        )
    if interval == "minute" and unit not in _MINUTE_UNITS:
        raise HTTPException(
            status_code=400,
            detail={"error": "unit은 1, 5, 10 또는 30 이어야 합니다", "code": "BAD_UNIT"},
        )
    if interval == "minute" and scope not in ("today", "session"):
        raise HTTPException(
            status_code=400,
            detail={"error": 'scope은 "today" 또는 "session"이어야 합니다', "code": "BAD_SCOPE"},
        )
    try:
        if interval == "minute":
            candles = await get_minute_chart(symbol, unit, scope)
        elif interval == "weekly":
            candles = await get_weekly_chart(symbol)
        else:
            candles = await get_daily_chart(symbol)
    except ChartUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": str(exc) or "차트를 일시적으로 불러올 수 없습니다", "code": "CHART_UNAVAILABLE"},
        ) from exc
    return {"data": {"symbol": symbol, "interval": interval, "unit": unit, "scope": scope, "candles": candles}}
