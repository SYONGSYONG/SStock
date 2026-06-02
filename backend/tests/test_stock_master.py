"""종목 마스터(.mst) 종목명 조회 테스트."""

from __future__ import annotations

from app.stocks.master import count, get_name, search


def test_종목명_조회():
    assert get_name("005930") == "삼성전자"
    assert get_name("000660") == "SK하이닉스"


def test_마스터_로드_규모():
    # 코스피+코스닥 합산 수천 종목
    assert count() > 1000


def test_없는_코드는_None():
    assert get_name("999999") is None


def test_종목명으로_검색():
    results = search("삼성전자")
    codes = {r["symbol"] for r in results}
    assert "005930" in codes
    # 첫 결과가 정확히 '삼성전자'
    assert results[0]["name"] == "삼성전자"


def test_코드_접두_검색():
    results = search("0059")
    assert any(r["symbol"] == "005930" for r in results)


def test_빈_쿼리는_빈_결과():
    assert search("   ") == []
