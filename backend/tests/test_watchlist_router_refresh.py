"""관심종목 변경 시 실시간 구독 갱신 테스트."""

from __future__ import annotations

import httpx
from starlette.testclient import TestClient

from app.bot import market_data
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


def test_관심종목_추가시_실시간재구독(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", s.database_path)
    get_settings.cache_clear()
    calls: list[list[str]] = []

    async def fake_refresh(symbols):
        calls.append(list(symbols))

    monkeypatch.setattr(market_data.market_data_service, "refresh", fake_refresh)

    try:
        with TestClient(app) as client:
            res = client.post("/api/watchlist", json={"symbol": "005930", "name": "삼성전자"})
        assert res.status_code == 201
        assert calls == [["005930"]]
    finally:
        get_settings.cache_clear()


def test_관심종목_삭제시_실시간재구독(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", s.database_path)
    get_settings.cache_clear()
    calls: list[list[str]] = []

    async def fake_refresh(symbols):
        calls.append(list(symbols))

    monkeypatch.setattr(market_data.market_data_service, "refresh", fake_refresh)

    try:
        with TestClient(app) as client:
            add = client.post("/api/watchlist", json={"symbol": "005930", "name": "삼성전자"})
            assert add.status_code == 201
            res = client.delete("/api/watchlist/005930")
        assert res.status_code == 200
        assert calls[-1] == []
    finally:
        get_settings.cache_clear()
