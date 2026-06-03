"""관심종목 변경 시 실시간 구독 갱신 테스트."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.bot.registry import get_registry, reset_registry
from app.config import Settings, get_settings
from app.main import app


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="00000000",
        database_path=str(tmp_path / "sstock.db"),
    )


def _patch_feed_refresh(monkeypatch) -> list[list[str]]:
    """레지스트리의 모든 모드 피드 refresh를 가로채 호출 인자를 기록한다."""
    reset_registry()  # 현재 settings로 레지스트리 재구성
    calls: list[list[str]] = []

    async def fake_refresh(symbols):
        calls.append(list(symbols))

    for feed in get_registry().feeds().values():
        monkeypatch.setattr(feed, "refresh", fake_refresh)
    return calls


def test_관심종목_추가시_실시간재구독(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", s.database_path)
    get_settings.cache_clear()
    calls = _patch_feed_refresh(monkeypatch)

    try:
        with TestClient(app) as client:
            res = client.post("/api/watchlist", json={"symbol": "005930", "name": "삼성전자"})
        assert res.status_code == 201
        # 모든 모드 피드가 갱신되며, 마지막 호출은 갱신된 심볼 목록
        assert calls and all(c == ["005930"] for c in calls)
    finally:
        get_settings.cache_clear()
        reset_registry()


def test_관심종목_삭제시_실시간재구독(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", s.database_path)
    get_settings.cache_clear()
    calls = _patch_feed_refresh(monkeypatch)

    try:
        with TestClient(app) as client:
            add = client.post("/api/watchlist", json={"symbol": "005930", "name": "삼성전자"})
            assert add.status_code == 201
            res = client.delete("/api/watchlist/005930")
        assert res.status_code == 200
        assert calls[-1] == []
    finally:
        get_settings.cache_clear()
        reset_registry()
