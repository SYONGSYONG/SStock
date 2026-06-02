"""종목 차트(일봉/분봉) 라우터.

GET /api/charts/{symbol}?interval=daily|minute
- 시세 데이터라 모드 무관. KIS 오류 시에도 빈 캔들로 graceful 응답.
설계: docs/07-chart.md.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.kis.charts import get_daily_chart, get_minute_chart

router = APIRouter(prefix="/api/charts", tags=["charts"])

_INTERVALS = ("daily", "minute")


@router.get("/{symbol}")
async def chart(
    symbol: str,
    interval: str = Query(default="daily"),
) -> dict:
    if interval not in _INTERVALS:
        raise HTTPException(
            status_code=400,
            detail={"error": "interval은 daily 또는 minute 이어야 합니다", "code": "BAD_INTERVAL"},
        )
    if interval == "minute":
        candles = await get_minute_chart(symbol)
    else:
        candles = await get_daily_chart(symbol)
    return {"data": {"symbol": symbol, "interval": interval, "candles": candles}}
