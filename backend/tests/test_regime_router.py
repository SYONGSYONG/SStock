"""오토모드 국면 조회 라우터 테스트(2단계)."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.bot.registry import get_registry, reset_registry
from app.main import app


def test_국면_조회_엔드포인트():
    """봇이 분류한 종목별 국면을 모드별로 반환한다."""
    reset_registry()
    get_registry().get_bot("paper")._last_regime["005930"] = "강한상승"
    try:
        with TestClient(app) as c:
            body = c.get("/api/regime?mode=paper").json()["data"]
            assert body["005930"] == "강한상승"
            # 다른 모드는 비어 있다(국면은 봇 인스턴스별)
            assert c.get("/api/regime?mode=live").json()["data"] == {}
    finally:
        reset_registry()


def test_잘못된_모드는_400():
    with TestClient(app) as c:
        r = c.get("/api/regime?mode=foo")
        assert r.status_code == 400
        assert r.json()["code"] == "BAD_MODE"
