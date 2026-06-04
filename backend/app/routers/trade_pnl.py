"""기간별 매매손익 라우터.

KIS HTS [0856] 기간별매매손익 화면(API: TTTC8715R 기간별매매손익현황조회)에 대응하는
조회. 봇의 주문 이력(`orders`) 기반 로컬 계산을 사용한다(모의·실전 동일). 수수료·세금은
추정치(`estimated=True`).

[하이브리드 seam] 실전 모드에서 실제 수수료·세금까지 정확히 보려면 KIS `TTTC8715R`을
연동할 수 있으나, 해당 API는 모의투자 미지원이며 레퍼런스 문서에 전체 출력 필드 스펙이
없어 현재는 로컬 계산을 사용한다. 정확한 필드 스펙 확보 시 live 분기를 추가한다.
"""

from __future__ import annotations

import logging
import re
import sqlite3

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.db.database import get_db
from app.kis import trade_pnl as kis_trade_pnl
from app.services import trade_pnl_service

router = APIRouter(prefix="/api/trade-pnl", tags=["trade-pnl"])

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(value: str | None, field: str) -> None:
    if value is not None and not _DATE_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail={"error": f"{field}는 YYYY-MM-DD 형식이어야 합니다", "code": "BAD_DATE"},
        )


@router.get("")
async def get_trade_pnl(
    mode: str = Query(default="paper"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    sort: str = Query(default="desc"),
    conn: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """기간별 매매손익(행 + 요약)을 반환한다.

    실전(live)은 KIS API(TTTC8715R, 실제 수수료·세금 반영)를, 모의(paper)는 봇 주문
    이력 기반 로컬 계산(수수료·세금 추정)을 사용한다. KIS 오류 시 빈 결과(available=False).
    """
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    if sort not in ("desc", "asc"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 정렬", "code": "BAD_SORT"})
    _validate_date(start, "start")
    _validate_date(end, "end")
    if symbol is not None and not re.fullmatch(r"\d{6}", symbol):
        raise HTTPException(
            status_code=400, detail={"error": "종목코드는 6자리 숫자", "code": "BAD_SYMBOL"}
        )

    if mode == "live":
        try:
            data = await kis_trade_pnl.get_period_trade_profit(
                settings, mode="live", start=start, end=end, symbol=symbol, sort=sort
            )
            return {"data": data}
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            # KIS 장애/자격증명 누락 등 → 대시보드가 깨지지 않게 빈 결과로 graceful 처리
            logger.warning("KIS 기간별매매손익 조회 실패[live]: %s", exc)
            return {
                "data": {
                    "rows": [],
                    "summary": trade_pnl_service.summarize([]),
                    "source": "kis",
                    "estimated": False,
                    "available": False,
                    "period": {"start": start, "end": end},
                }
            }

    data = trade_pnl_service.compute_trade_pnl(
        conn, mode=mode, start=start, end=end, symbol=symbol, sort=sort
    )
    return {"data": data}
