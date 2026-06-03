"""분야별 추천 복합 점수 서비스.

각 세부 지표를 분야(후보 집합) 내 **순위 백분위**(0~100)로 정규화한 뒤,
축별로 가중평균하고 축을 다시 가중합해 종합 점수를 만든다.

종합 = 0.40·모멘텀 + 0.35·펀더멘털 + 0.25·수급   (각 축 0~100)
  - 모멘텀  = 등락률(50%) + 거래량(50%)
  - 펀더멘털 = ROE(20/35) + 영업이익(15/35)
  - 수급    = 외국인(15/25) + 기관(10/25)

데이터가 없는(None) 지표는 중립(50)으로 degrade 한다.
설계 근거: docs/06-recommend.md §3.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.stocks import sector

# 축 가중치 (docs/06-recommend.md §9 확정값)
_W_MOMENTUM = 0.40
_W_FUNDAMENTAL = 0.35
_W_SUPPLY = 0.25

_NEUTRAL = 50.0

# 하이브리드 파이프라인 기본값 (docs/06-recommend.md §9)
DEFAULT_CANDIDATE_LIMIT = 30  # 1차 압축 N
DEFAULT_RESULT_LIMIT = 10  # 추천 개수 K

# KIS rate limit 대비: 동시 조회 상한 + 결과 캐시(TTL) (docs/06-recommend.md §4·§7)
# KisClient의 전역 세마포어(_GLOBAL_SEMAPHORE=3)와 보조를 맞추어 동시성 제한.
_MAX_CONCURRENCY = 3
_CACHE_TTL_SEC = 300.0

PriceFn = Callable[[str], Awaitable[dict[str, Any]]]
FlowFn = Callable[[str], Awaitable[dict[str, Any]]]

# theme+limit → (저장시각, 결과). 모듈 전역 단순 TTL 캐시.
_cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}


def clear_cache() -> None:
    """추천 결과 캐시를 비운다(테스트·강제 갱신용)."""
    _cache.clear()


def _percentile_ranks(values: list[float | None]) -> list[float]:
    """분야 내 순위 백분위(0~100). None과 단일 표본은 중립(50)으로 둔다.

    동점은 평균 순위를 공유한다(같은 값 → 같은 백분위).
    """
    present = [(i, v) for i, v in enumerate(values) if v is not None]
    ranks = [_NEUTRAL] * len(values)
    n = len(present)
    if n <= 1:
        return ranks
    order = sorted(present, key=lambda t: t[1])
    denom = n - 1
    j = 0
    while j < n:
        k = j
        while k + 1 < n and order[k + 1][1] == order[j][1]:
            k += 1
        avg_rank = (j + k) / 2.0  # 동점 그룹의 평균 순위
        for t in range(j, k + 1):
            ranks[order[t][0]] = avg_rank / denom * 100.0
        j = k + 1
    return ranks


def _column(cands: list[dict[str, Any]], key: str) -> list[float | None]:
    out: list[float | None] = []
    for c in cands:
        v = c.get(key)
        out.append(float(v) if isinstance(v, (int, float)) else None)
    return out


def score_candidates(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """후보 종목에 복합 점수를 매겨 종합점수 내림차순으로 반환한다."""
    if not cands:
        return []

    roe = _percentile_ranks(_column(cands, "roe"))
    op = _percentile_ranks(_column(cands, "op_profit"))
    chg = _percentile_ranks(_column(cands, "change_rate"))
    vol = _percentile_ranks(_column(cands, "volume"))
    frn = _percentile_ranks(_column(cands, "foreign_net"))
    ins = _percentile_ranks(_column(cands, "inst_net"))

    scored: list[dict[str, Any]] = []
    for i, c in enumerate(cands):
        momentum = chg[i] * 0.5 + vol[i] * 0.5
        fundamental = roe[i] * (20 / 35) + op[i] * (15 / 35)
        supply = frn[i] * (15 / 25) + ins[i] * (10 / 25)
        score = (
            momentum * _W_MOMENTUM
            + fundamental * _W_FUNDAMENTAL
            + supply * _W_SUPPLY
        )
        scored.append(
            {
                **c,
                "score": round(score, 1),
                "momentum": round(momentum, 1),
                "fundamental": round(fundamental, 1),
                "supply": round(supply, 1),
            }
        )

    scored.sort(key=lambda r: -r["score"])
    return scored


async def _enrich_stock(
    stock: dict[str, Any],
    price_fn: PriceFn,
    flow_fn: FlowFn,
    sem: asyncio.Semaphore,
) -> dict[str, Any]:
    """종목 정보를 현재가와 수급 정보로 풍부하게 한다."""
    async with sem:  # 동시 KIS 호출 상한
        price, flow = await asyncio.gather(
            price_fn(stock["symbol"]), flow_fn(stock["symbol"])
        )
    return {
        **stock,
        "price": price.get("price"),
        "change_rate": price.get("change_rate"),
        "volume": price.get("volume"),
        "foreign_net": flow.get("foreign_net"),
        "inst_net": flow.get("inst_net"),
    }


async def stream_recommend_for_theme(
    theme: str,
    limit: int = DEFAULT_RESULT_LIMIT,
    *,
    price_fn: PriceFn,
    flow_fn: FlowFn,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    use_cache: bool = True,
):
    """스트리밍 하이브리드 파이프라인: 후보 → 시세 스트리밍 → 최종 점수.

    (event_name: str, payload: dict) 튜플을 yield하는 async generator.
    이벤트 순서: candidates → quote* → result (또는 캐시 히트 시 candidates → result).
    """
    key = (theme, limit)

    # 캐시 히트 → 빠른 경로
    if use_cache:
        hit = _cache.get(key)
        if hit is not None and time.monotonic() - hit[0] < _CACHE_TTL_SEC:
            result = hit[1]
            yield (
                "candidates",
                {
                    "theme": result["theme"],
                    "base_date": result["base_date"],
                    "candidates": [
                        {"symbol": item["symbol"], "name": item.get("name"), "market": item.get("market")}
                        for item in result["items"]
                    ],
                },
            )
            yield ("result", result)
            return

    # 로컬 후보 조회
    base = sector.by_theme(theme)[:candidate_limit]

    # 후보 이벤트 발송
    candidates_payload = {
        "theme": theme,
        "base_date": base[0].get("base_date") if base else None,
        "candidates": [
            {"symbol": s["symbol"], "name": s.get("name"), "market": s.get("market")}
            for s in base
        ],
    }
    yield ("candidates", candidates_payload)

    # 후보가 없으면 빈 결과로 종료
    if not base:
        result = {"theme": theme, "base_date": None, "items": []}
        if use_cache:
            _cache[key] = (time.monotonic(), result)
        yield ("result", result)
        return

    # 세마포어로 동시 호출 제한
    sem = asyncio.Semaphore(_MAX_CONCURRENCY)

    # 태스크 생성 및 완료 순서대로 quote 이벤트 발송
    tasks = [_enrich_stock(s, price_fn, flow_fn, sem) for s in base]
    enriched_dict: dict[str, dict[str, Any]] = {}

    for coro in asyncio.as_completed(tasks):
        enriched = await coro
        enriched_dict[enriched["symbol"]] = enriched
        # quote 이벤트 발송: symbol, price, change_rate, volume만 포함
        yield (
            "quote",
            {
                "symbol": enriched["symbol"],
                "price": enriched.get("price"),
                "change_rate": enriched.get("change_rate"),
                "volume": enriched.get("volume"),
            },
        )

    # 모든 종목을 base 순서대로 정렬하여 점수 계산
    enriched_list = [enriched_dict[s["symbol"]] for s in base if s["symbol"] in enriched_dict]
    scored = score_candidates(enriched_list)

    # 최종 결과 저장 및 발송
    result = {
        "theme": theme,
        "base_date": base[0].get("base_date"),
        "items": scored[:limit],
    }
    if use_cache:
        _cache[key] = (time.monotonic(), result)
    yield ("result", result)


async def recommend_for_theme(
    theme: str,
    limit: int = DEFAULT_RESULT_LIMIT,
    *,
    price_fn: PriceFn,
    flow_fn: FlowFn,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    use_cache: bool = True,
) -> dict[str, Any]:
    """하이브리드 파이프라인: 로컬 테마 필터 → 후보 압축 → 후보만 시세·수급 조회 → 랭킹.

    price_fn/flow_fn은 종목코드를 받아 비동기로 시세/수급 dict를 반환한다(주입).
    KIS rate limit 대비: 후보 조회를 세마포어로 제한하고, 결과를 TTL 동안 캐시한다.
    """
    key = (theme, limit)
    if use_cache:
        hit = _cache.get(key)
        if hit is not None and time.monotonic() - hit[0] < _CACHE_TTL_SEC:
            return hit[1]

    base = sector.by_theme(theme)[:candidate_limit]
    if not base:
        result = {"theme": theme, "base_date": None, "items": []}
        if use_cache:
            _cache[key] = (time.monotonic(), result)
        return result

    sem = asyncio.Semaphore(_MAX_CONCURRENCY)
    enriched = await asyncio.gather(*[_enrich_stock(s, price_fn, flow_fn, sem) for s in base])
    scored = score_candidates(list(enriched))
    result = {
        "theme": theme,
        "base_date": base[0].get("base_date"),
        "items": scored[:limit],
    }
    if use_cache:
        _cache[key] = (time.monotonic(), result)
    return result
