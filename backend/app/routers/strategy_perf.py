"""섀도우 성과 보드 라우터 — 신호 기반 가상 성과 조회.

신호(`signals`)만으로 (종목,전략)별 가상 성과(완결 거래 = BUY→SELL 페어, 수익률 %)를
계산해 반환한다. 실제 주문·전략 전환과 무관(위험 0). ON·OFF(관찰) 신호 모두 포함.
"""

from __future__ import annotations

import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.database import get_db
from app.services import strategy_perf_service

router = APIRouter(prefix="/api/strategy-performance", tags=["strategy-performance"])

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("")
async def get_strategy_performance(
    mode: str = Query(default="paper"),
    start: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """모드별 (종목,전략) 가상 성과 보드를 반환한다.

    start('YYYY-MM-DD', KST) 지정 시 기간 필터(해당 일자 이후 신호만 집계).
    """
    if mode not in ("paper", "live"):
        raise HTTPException(
            status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"}
        )
    if start is not None and not _DATE_RE.match(start):
        raise HTTPException(
            status_code=400,
            detail={"error": "start는 YYYY-MM-DD 형식이어야 합니다", "code": "BAD_DATE"},
        )
    data = strategy_perf_service.compute_strategy_performance(conn, mode=mode, start=start)
    return {"data": data}
