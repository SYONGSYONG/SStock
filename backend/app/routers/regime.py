"""오토모드: 종목별 현재 시장 국면 조회 라우터(2단계 추천 프리셋용)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.bot.registry import get_registry

router = APIRouter(prefix="/api/regime", tags=["regime"])


@router.get("")
def current_regimes(mode: str = Query(default="paper")) -> dict:
    """모드별 봇이 마지막으로 분류한 종목별 시장 국면을 반환한다.

    봇이 켜져 동작하는 동안 갱신되며, 정지 시에는 마지막 분류값이 남는다.
    응답: { "data": { "005930": "강한상승", ... } }
    """
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail={"error": "잘못된 모드", "code": "BAD_MODE"})
    bot = get_registry().get_bot(mode)
    return {"data": bot.regimes()}
