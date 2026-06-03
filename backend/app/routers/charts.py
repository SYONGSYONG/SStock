"""종목 차트(일봉/분봉) 라우터.

GET /api/charts/{symbol}?interval=daily|minute
- 시세 데이터라 모드 무관. KIS 오류 시에도 빈 캔들로 graceful 응답.
설계: docs/07-chart.md.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.kis.charts import ChartUnavailableError, get_daily_chart, get_minute_chart

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
    try:
        if interval == "minute":
            candles = await get_minute_chart(symbol)
        else:
            candles = await get_daily_chart(symbol)
    except ChartUnavailableError as exc:
        # 일시 오류는 '데이터 없음(빈 캔들)'과 구분해 503으로 알린다.
        # 프론트가 [다시 시도] UI를 띄우고 자동 재시도하도록 한다.
        raise HTTPException(
            status_code=503,
            detail={"error": str(exc) or "차트를 일시적으로 불러올 수 없습니다", "code": "CHART_UNAVAILABLE"},
        ) from exc
    return {"data": {"symbol": symbol, "interval": interval, "candles": candles}}
