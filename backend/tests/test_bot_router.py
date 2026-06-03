"""봇 라우터 — 실전 전환 안전 게이트 테스트."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _live_settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="live",
        kis_paper_app_key="k",
        kis_paper_app_secret="s",
        kis_paper_account_no="00000000",
    )


def test_실전_봇시작은_확인없이_409():
    """실전 모드에서 명시적 확인 없으면 409."""
    app.dependency_overrides[get_settings] = _live_settings
    try:
        with TestClient(app) as c:
            # mode=live로 명시, confirm_live=false
            r = c.post("/api/bot/start?mode=live", json={"confirm_live": False})
            assert r.status_code == 409
            body = r.json()
            assert body["code"] == "LIVE_CONFIRM_REQUIRED"
    finally:
        app.dependency_overrides.clear()


def test_봇_상태에_모드_포함():
    """봇 상태 응답에 모드 포함."""
    with TestClient(app) as c:
        body = c.get("/api/bot/status?mode=paper").json()["data"]
        assert body["running"] is False
        assert body["mode"] == "paper"
