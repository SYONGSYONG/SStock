"""스트리밍 추천 서비스 테스트.

stream_recommend_for_theme가 단계적으로 이벤트를 발송하는지 검증한다.
"""

from __future__ import annotations

from app.services import recommend_service


async def test_스트림이_candidates_quote_result_순서로_발송한다():
    """후보 정보 → 종목별 시세 → 최종 결과 순서 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100, "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    events = []
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    ):
        events.append((event_name, payload))

    # 이벤트 순서 검증
    assert len(events) >= 3
    assert events[0][0] == "candidates"
    assert events[-1][0] == "result"

    # quote 이벤트는 candidates 후, result 전에 있어야 함
    quote_events = [e for e in events if e[0] == "quote"]
    assert len(quote_events) > 0


async def test_candidates_이벤트에_후보_목록이_포함된다():
    """candidates 이벤트에 symbol, name, market이 포함되는지 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100, "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    ):
        if event_name == "candidates":
            assert "candidates" in payload
            assert "theme" in payload
            assert "base_date" in payload
            assert payload["theme"] == "bank"
            # 각 후보에 symbol, name, market 있는지 검증
            for cand in payload["candidates"]:
                assert "symbol" in cand
                assert "name" in cand
                assert "market" in cand
            break


async def test_quote_이벤트에_symbol_price_포함():
    """quote 이벤트에 symbol, price, change_rate, volume이 포함되는지 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100 + len(symbol), "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    quote_count = 0
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    ):
        if event_name == "quote":
            quote_count += 1
            assert "symbol" in payload
            assert "price" in payload
            assert "change_rate" in payload
            assert "volume" in payload

    assert quote_count > 0  # 최소 1개 이상의 quote 이벤트


async def test_result_이벤트에_최종_점수_포함():
    """result 이벤트에 theme, base_date, items가 포함되고 점수로 정렬되는지 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100, "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    result_payload = None
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    ):
        if event_name == "result":
            result_payload = payload
            break

    assert result_payload is not None
    assert result_payload["theme"] == "bank"
    assert "items" in result_payload
    assert "base_date" in result_payload

    # 최대 limit개까지만 반환
    assert len(result_payload["items"]) <= 5

    # 점수 내림차순 정렬 검증
    items = result_payload["items"]
    if len(items) > 1:
        scores = [item["score"] for item in items]
        assert scores == sorted(scores, reverse=True)


async def test_캐시_히트하면_quote_이벤트_없이_candidates와_result만():
    """캐시 적중 시 quote 이벤트를 스킵하고 바로 result를 반환하는지 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100, "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    # 첫 번째 호출: 캐시 저장
    events1 = []
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=True
    ):
        events1.append(event_name)

    # 두 번째 호출: 캐시 적중
    events2 = []
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "bank", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=True
    ):
        events2.append(event_name)

    # 캐시 적중 경로: candidates → result (quote 없음)
    assert events2 == ["candidates", "result"]
    recommend_service.clear_cache()


async def test_빈_후보는_빈_결과로_종료():
    """후보가 없는 테마는 빈 candidates와 빈 items로 종료하는지 검증."""
    recommend_service.clear_cache()

    async def price_fn(symbol):
        return {"price": 100, "change_rate": 1.0, "volume": 1000}

    async def flow_fn(symbol):
        return {"foreign_net": 100, "inst_net": 200}

    events = []
    async for event_name, payload in recommend_service.stream_recommend_for_theme(
        "unknown_theme_xyzabc", 5, price_fn=price_fn, flow_fn=flow_fn, use_cache=False
    ):
        events.append((event_name, payload))

    # 빈 후보 경로: candidates(empty) → result(empty)
    assert len(events) >= 2
    assert events[0][0] == "candidates"
    assert events[0][1]["candidates"] == []
    assert events[-1][0] == "result"
    assert events[-1][1]["items"] == []
