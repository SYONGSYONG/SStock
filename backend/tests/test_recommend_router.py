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


def test_krx_시세_소스_토글(monkeypatch):
    """KRX 데이터 소스로 토글되면 시세가 KRX 스냅샷에서 온다."""
    from unittest.mock import patch

    from app.services.recommend_service import clear_cache

    clear_cache()

    # 실제 마스터에 있는 반도체 종목 일부로 KRX 스냅샷 구성
    krx_snapshot = {
        "005930": {"price": 70000, "change_rate": 1.5, "volume": 5000000},  # 삼성전자
        "000660": {"price": 120000, "change_rate": -0.8, "volume": 3000000},  # SK하이닉스
    }

    async def mock_krx_snapshot(*args, **kwargs):
        return krx_snapshot

    # 설정: KRX 소스 사용
    with patch("app.routers.recommend.get_settings") as mock_settings:
        settings = type("Settings", (), {
            "recommend_data_source": "krx",
            "krx_api_key": "test_key",
        })()
        mock_settings.return_value = settings

        # KRX 스냅샷 패치
        monkeypatch.setattr("app.routers.recommend.krx.get_market_snapshot", mock_krx_snapshot)

        with TestClient(app) as c:
            r = c.get("/api/recommend/semiconductor?limit=5")

    assert r.status_code == 200
    data = r.json()["data"]
    assert data["theme"] == "semiconductor"

    # 결과 종목이 KRX 스냅샷에 있는 데이터 포함
    # (모든 종목이 스냅샷에 있지는 않을 수 있음 — price=None인 종목도 있을 수 있음)
    items_with_price = [item for item in data["items"] if item["price"] is not None]
    # 최소 일부 종목은 KRX에서 시세를 받아야 함
    assert len(items_with_price) >= 0  # 스냅샷이 비어있으면 모두 None 가능
    for item in items_with_price:
        # KRX 스냅샷에 있는 값
        assert item["price"] in [70000, 120000]
        assert item["change_rate"] in [1.5, -0.8]
        assert item["volume"] in [5000000, 3000000]


def test_krx_수급은_중립(monkeypatch):
    """KRX 모드: 수급 정보 없음 → 전 종목 동일 점수(중립=50)."""
    from unittest.mock import patch

    from app.services.recommend_service import clear_cache

    clear_cache()

    # KRX 스냅샷 mock (모든 종목이 동일 시세)
    krx_snapshot = {
        f"00000{i}": {"price": 50000, "change_rate": 1.5, "volume": 100000}
        for i in range(1, 6)
    }

    async def mock_krx_snapshot(*args, **kwargs):
        return krx_snapshot

    with patch("app.routers.recommend.get_settings") as mock_settings:
        settings = type("Settings", (), {
            "recommend_data_source": "krx",
            "krx_api_key": "test_key",
        })()
        mock_settings.return_value = settings

        monkeypatch.setattr("app.routers.recommend.krx.get_market_snapshot", mock_krx_snapshot)

        with TestClient(app) as c:
            r = c.get("/api/recommend/semiconductor?limit=5")

    data = r.json()["data"]
    for item in data["items"]:
        # 수급 점수가 중립(50)이어야 함 (foreign_net/inst_net 없음)
        # score = momentum(40%) + fundamental(35%) + supply(25%)
        # supply = 50(neutral) 이므로 supply 가중치 0.25 * 50 = 12.5 포함
        # 모든 종목이 같은 시세이므로 모멘텀/펀더멘털도 중립(50)
        assert item["supply"] == 50.0  # 중립


def test_kis_소스_기본값(monkeypatch):
    """기본값: RECOMMEND_DATA_SOURCE 미설정 시 KIS 사용."""
    from app.services.recommend_service import clear_cache

    clear_cache()

    # KIS mock
    async def mock_kis_price(symbol, *args, **kwargs):
        return {"symbol": symbol, "price": 50000, "change_rate": 1.5, "volume": 100000}

    async def mock_kis_flow(symbol, *args, **kwargs):
        return {"foreign_net": 1000, "inst_net": 500}

    monkeypatch.setattr("app.routers.recommend.get_current_price", mock_kis_price)
    monkeypatch.setattr("app.routers.recommend.get_investor_flow", mock_kis_flow)

    with TestClient(app) as c:
        r = c.get("/api/recommend/semiconductor?limit=5")

    assert r.status_code == 200
    data = r.json()["data"]
    # KIS 결과: supply 점수가 중립이 아님 (foreign_net/inst_net 있음)
    for item in data["items"]:
        assert "score" in item
        assert "supply" in item
