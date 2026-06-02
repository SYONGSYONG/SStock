"""분야별 추천 라우터 테스트 (KIS 시세·수급은 monkeypatch로 대체)."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.main import app


async def _fake_price(symbol: str, *args, **kwargs) -> dict:
    return {"price": 50000, "change_rate": 1.5, "volume": 100000}


async def _fake_flow(symbol: str, *args, **kwargs) -> dict:
    return {"foreign_net": 1000, "inst_net": 500}


def _patch_kis(monkeypatch) -> None:
    from app.services.recommend_service import clear_cache

    clear_cache()  # 테스트 간 캐시 격리
    monkeypatch.setattr("app.routers.recommend.get_current_price", _fake_price)
    monkeypatch.setattr("app.routers.recommend.get_investor_flow", _fake_flow)


def test_테마_목록_조회():
    with TestClient(app) as c:
        data = c.get("/api/recommend/themes").json()["data"]
    slugs = {t["slug"] for t in data}
    assert len(data) == 12
    assert "semiconductor" in slugs
    assert all("count" in t and "label" in t for t in data)


def test_테마_추천_조회(monkeypatch):
    _patch_kis(monkeypatch)
    with TestClient(app) as c:
        r = c.get("/api/recommend/semiconductor?limit=5")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["theme"] == "semiconductor"
    assert len(data["items"]) <= 5
    for item in data["items"]:
        assert {"symbol", "name", "score", "momentum", "fundamental", "supply"} <= set(item)


def test_추천은_점수_내림차순(monkeypatch):
    _patch_kis(monkeypatch)
    with TestClient(app) as c:
        items = c.get("/api/recommend/auto?limit=10").json()["data"]["items"]
    scores = [i["score"] for i in items]
    assert scores == sorted(scores, reverse=True)


def test_알수없는_테마는_404():
    with TestClient(app) as c:
        r = c.get("/api/recommend/unknown_theme")
    assert r.status_code == 404
    assert r.json()["code"] == "UNKNOWN_THEME"
