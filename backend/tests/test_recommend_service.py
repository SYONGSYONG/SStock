"""복합 점수 추천 서비스 테스트.

점수 = 0.40·모멘텀 + 0.35·펀더멘털 + 0.25·수급 (각 축 0~100, 분야 내 순위 백분위).
데이터가 없는 지표는 중립(50)으로 degrade 한다.
"""

from __future__ import annotations

from app.services import recommend_service
from app.services.recommend_service import score_candidates


def _cand(symbol, roe=None, op=None, chg=None, vol=None, frn=None, ins=None):
    return {
        "symbol": symbol, "name": symbol, "market": "KOSPI",
        "roe": roe, "op_profit": op, "change_rate": chg,
        "volume": vol, "foreign_net": frn, "inst_net": ins,
    }


def test_빈_입력은_빈_결과():
    assert score_candidates([]) == []


def test_모든_지표_1위면_종합점수_최고():
    cands = [
        _cand("AAA", roe=30, op=300, chg=9, vol=900, frn=900, ins=900),
        _cand("BBB", roe=20, op=200, chg=5, vol=500, frn=500, ins=500),
        _cand("CCC", roe=10, op=100, chg=1, vol=100, frn=100, ins=100),
    ]
    ranked = score_candidates(cands)
    assert ranked[0]["symbol"] == "AAA"
    assert ranked[0]["score"] == 100.0
    assert ranked[-1]["symbol"] == "CCC"
    assert ranked[-1]["score"] == 0.0


def test_결과는_점수_내림차순_정렬():
    cands = [
        _cand("LOW", roe=1, op=1, chg=1, vol=1, frn=1, ins=1),
        _cand("HIGH", roe=99, op=99, chg=99, vol=99, frn=99, ins=99),
    ]
    ranked = score_candidates(cands)
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_데이터_전무하면_모든_축_중립50():
    cands = [_cand("AAA"), _cand("BBB")]
    ranked = score_candidates(cands)
    for r in ranked:
        assert r["momentum"] == 50.0
        assert r["fundamental"] == 50.0
        assert r["supply"] == 50.0
        assert r["score"] == 50.0


def test_펀더멘털만_있으면_ROE_높은_종목이_펀더멘털_우위():
    cands = [
        _cand("HIGH_ROE", roe=40, op=100),
        _cand("LOW_ROE", roe=5, op=100),
    ]
    ranked = {r["symbol"]: r for r in score_candidates(cands)}
    assert ranked["HIGH_ROE"]["fundamental"] > ranked["LOW_ROE"]["fundamental"]


def test_세부_축_점수가_결과에_포함된다():
    ranked = score_candidates([_cand("AAA", roe=10, chg=3)])
    r = ranked[0]
    assert {"score", "momentum", "fundamental", "supply"} <= set(r)


def test_동점은_같은_백분위를_공유한다():
    # ROE·영업이익 동점 3종목 + 낮은 1종목 → 동점자 펀더멘털 동일, 낮은 종목보다 우위
    cands = [
        _cand("A", roe=10, op=10), _cand("B", roe=10, op=10),
        _cand("C", roe=10, op=10), _cand("D", roe=1, op=1),
    ]
    ranked = {r["symbol"]: r for r in score_candidates(cands)}
    assert ranked["A"]["fundamental"] == ranked["B"]["fundamental"] == ranked["C"]["fundamental"]
    assert ranked["A"]["fundamental"] > ranked["D"]["fundamental"]


async def test_캐시_적중하면_재조회하지_않는다():
    recommend_service.clear_cache()
    calls = {"price": 0, "flow": 0}

    async def price_fn(symbol):
        calls["price"] += 1
        return {"price": 1, "change_rate": 1.0, "volume": 1}

    async def flow_fn(symbol):
        calls["flow"] += 1
        return {"foreign_net": 1, "inst_net": 1}

    r1 = await recommend_service.recommend_for_theme("bank", 5, price_fn=price_fn, flow_fn=flow_fn)
    first_calls = calls["price"]
    r2 = await recommend_service.recommend_for_theme("bank", 5, price_fn=price_fn, flow_fn=flow_fn)

    assert calls["price"] == first_calls  # 두 번째는 캐시 적중 → 추가 호출 없음
    assert r1 == r2
    recommend_service.clear_cache()


async def test_use_cache_False면_매번_조회한다():
    recommend_service.clear_cache()
    calls = {"n": 0}

    async def price_fn(symbol):
        calls["n"] += 1
        return {"price": 1, "change_rate": 1.0, "volume": 1}

    async def flow_fn(symbol):
        return {"foreign_net": 1, "inst_net": 1}

    await recommend_service.recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    )
    after_first = calls["n"]
    await recommend_service.recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    )
    assert calls["n"] == after_first * 2  # 캐시 미사용 → 다시 전부 조회
