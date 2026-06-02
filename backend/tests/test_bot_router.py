"""봇 라우터 — 실전 전환 안전 게이트 테스트."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _live_settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="live",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="50191231",
    )


def test_실전_봇시작은_확인없이_409():
    app.dependency_overrides[get_settings] = _live_settings
    try:
        with TestClient(app) as c:
            r = c.post("/api/bot/start", json={"confirm_live": False})
            assert r.status_code == 409
            assert r.json()["code"] == "LIVE_CONFIRM_REQUIRED"
    finally:
        app.dependency_overrides.clear()


def test_봇_상태에_모드_포함():
    with TestClient(app) as c:
        body = c.get("/api/bot/status").json()["data"]
        assert body["running"] is False
        assert body["mode"] == "paper"
