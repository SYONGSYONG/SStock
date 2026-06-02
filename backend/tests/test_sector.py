"""종목 마스터(.mst) 분야(KRX 테마)·재무 파싱 테스트.

KIS 공식 파서(Reference/SampleCode/.../kis_kospi_code_mst.py)의 고정폭 오프셋을
근거로 한다. 실제 마스터 파일 데이터로 검증한다(2026-03-31 기준 데이터 기준).
"""

from __future__ import annotations

from app.stocks import sector


def test_테마_목록은_12개():
    themes = sector.list_themes()
    slugs = {t["slug"] for t in themes}
    assert len(themes) == 12
    assert "semiconductor" in slugs
    assert "auto" in slugs
    assert "bank" in slugs


def test_각_테마는_종목수를_가진다():
    themes = {t["slug"]: t for t in sector.list_themes()}
    # KRX 섹터지수 편입 종목(소수 정예) — 반도체/자동차/은행은 최소 1종목 이상
    assert themes["semiconductor"]["count"] >= 1
    assert themes["auto"]["count"] >= 1
    assert themes["bank"]["count"] >= 1


def test_SK하이닉스는_반도체_테마():
    stocks = sector.by_theme("semiconductor")
    codes = {s["symbol"] for s in stocks}
    assert "000660" in codes  # SK하이닉스


def test_현대차는_자동차_테마():
    stocks = sector.by_theme("auto")
    codes = {s["symbol"] for s in stocks}
    assert "005380" in codes  # 현대차


def test_종목은_재무지표를_가진다():
    stocks = sector.by_theme("semiconductor")
    hynix = next(s for s in stocks if s["symbol"] == "000660")
    assert hynix["name"] == "SK하이닉스"
    assert isinstance(hynix["roe"], float)
    assert hynix["roe"] > 0
    assert hynix["base_date"] == "20260331"
    assert hynix["market"] == "KOSPI"


def test_없는_테마는_빈_목록():
    assert sector.by_theme("does_not_exist") == []


def test_거래정지_관리종목은_제외된다():
    # 활성 종목만 반환한다(active=True 보장)
    for slug in ("semiconductor", "auto", "bank"):
        for s in sector.by_theme(slug):
            assert s["active"] is True
