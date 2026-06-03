"""네이버금융(WiseReport) 기업개요 스크래핑.

네이버금융 종목분석 '기업개요' 탭은 WiseReport iframe을 임베드한다.
그 iframe(`c1010001.aspx`)에서 기업개요 불릿(`<li class="dot_cmp">`)과
기준일(`[기준:YYYY.MM.DD]`)을 파싱해 반환한다.

스크래핑이라 네이버/WiseReport HTML 구조가 바뀌면 깨질 수 있으므로,
오류·구조 변경 시 예외를 전파하지 않고 빈 결과로 graceful 처리한다.
기업개요는 자주 바뀌지 않으므로 종목별 하루 캐시 + 단일비행으로 호출을 줄인다.
"""

from __future__ import annotations

import asyncio
import html as html_lib
import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://navercomp.wisereport.co.kr/v2/company"
_PAGE_PROFILE = "c1010001.aspx"  # 기업개요·시세·주주현황
_PAGE_DETAIL = "c1020001.aspx"  # 최근연혁·주요제품 매출구성
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

_OVERVIEW_TTL_SEC = 86400.0  # 하루
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_locks: dict[str, asyncio.Lock] = {}

# <li class="... dot_cmp ...">텍스트</li>  (기업개요 불릿)
_LI_RE = re.compile(r'<li[^>]*class="[^"]*dot_cmp[^"]*"[^>]*>(.*?)</li>', re.DOTALL)
# [기준:2026.06.02]
_BASE_DATE_RE = re.compile(r"\[기준\s*:\s*([0-9.]+)\]")
_TAG_RE = re.compile(r"<[^>]+>")

# 시세정보 표: <table id="cTB11"> 안의 <th>라벨</th><td>값</td> 쌍
_PRICE_TABLE_RE = re.compile(r'<table[^>]*id="cTB11".*?</table>', re.DOTALL)
_TH_TD_RE = re.compile(r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", re.DOTALL)
# 주주현황 표: <tr class="p_sJJ...">, 주주명은 title 속성, 수치는 num 셀
_SH_ROW_RE = re.compile(r'<tr class="p_sJJ[^"]*">(.*?)</tr>', re.DOTALL)
_TITLE_RE = re.compile(r'title="([^"]+)"')
_NUM_TD_RE = re.compile(r'<td[^>]*class="[^"]*num[^"]*"[^>]*>(.*?)</td>', re.DOTALL)

# 상세 페이지(c1020001): 최근연혁 표(cTB202) / 주요제품 매출구성 표(cTB203).
# 행마다 <th scope="row">라벨</th><td>값</td> 구조 → 행 단위로 첫 th/td를 뽑는다.
_HISTORY_TABLE_RE = re.compile(r'<table[^>]*id="cTB202".*?</table>', re.DOTALL)
_PRODUCT_TABLE_RE = re.compile(r'<table[^>]*id="cTB203".*?</table>', re.DOTALL)
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_TH_CELL_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.DOTALL)
_TD_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)


def clear_overview_cache() -> None:
    """기업개요 캐시를 비운다(테스트·강제 갱신용)."""
    _cache.clear()
    _locks.clear()


def _strip_tags(s: str) -> str:
    """내부 태그·HTML 엔티티 제거 + 공백 정리."""
    text = html_lib.unescape(_TAG_RE.sub("", s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_price(html: str) -> list[dict[str, str]]:
    """시세정보 표(cTB11)를 라벨/값 쌍 목록으로 파싱한다."""
    m = _PRICE_TABLE_RE.search(html)
    if not m:
        return []
    pairs: list[dict[str, str]] = []
    for label, value in _TH_TD_RE.findall(m.group(0)):
        ls, vs = _strip_tags(label), _strip_tags(value)
        if ls and vs:
            pairs.append({"label": ls, "value": vs})
    return pairs


def _parse_shareholders(html: str) -> list[dict[str, Any]]:
    """주주현황 표를 {주주명, 보유주식수, 보유지분%} 목록으로 파싱한다."""
    out: list[dict[str, Any]] = []
    for row in _SH_ROW_RE.findall(html):
        tm = _TITLE_RE.search(row)
        name = tm.group(1).strip() if tm else None
        nums = [_strip_tags(n) for n in _NUM_TD_RE.findall(row)]
        if name and nums:
            out.append(
                {
                    "name": name,
                    "shares": nums[0] if len(nums) > 0 else None,
                    "pct": nums[1] if len(nums) > 1 else None,
                }
            )
    return out


def _parse_th_td_table(html: str, table_re: re.Pattern[str], k1: str, k2: str) -> list[dict[str, str]]:
    """지정한 table을 행 단위로 {k1: 첫 th, k2: 첫 td} 목록으로 파싱한다.

    행마다 첫 th/td만 사용하므로, 헤더 행(th만 있고 td 없음)은 자동 제외된다.
    """
    m = table_re.search(html)
    if not m:
        return []
    out: list[dict[str, str]] = []
    for row in _TR_RE.findall(m.group(0)):
        th = _TH_CELL_RE.search(row)
        td = _TD_CELL_RE.search(row)
        if not th or not td:
            continue
        av, bv = _strip_tags(th.group(1)), _strip_tags(td.group(1))
        if av and bv:
            out.append({k1: av, k2: bv})
    return out


def _parse_profile(html: str) -> dict[str, Any]:
    """c1010001(기업개요·시세·주주현황·기준일) 파싱."""
    summary = [text for li in _LI_RE.findall(html) if (text := _strip_tags(li))]
    m = _BASE_DATE_RE.search(html)
    return {
        "base_date": m.group(1) if m else None,
        "summary": summary,
        "price": _parse_price(html),
        "shareholders": _parse_shareholders(html),
    }


def _parse_detail(html: str) -> dict[str, Any]:
    """c1020001(최근연혁·주요제품 매출구성) 파싱."""
    return {
        "history": _parse_th_td_table(html, _HISTORY_TABLE_RE, "date", "detail"),
        "products": _parse_th_td_table(html, _PRODUCT_TABLE_RE, "name", "pct"),
    }


def _empty_result(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "base_date": None,
        "summary": [],
        "price": [],
        "shareholders": [],
        "history": [],
        "products": [],
    }


async def _fetch_page(client: httpx.AsyncClient, page: str, symbol: str) -> str:
    """WiseReport 페이지 HTML을 가져온다. 오류 시 빈 문자열(graceful)."""
    try:
        resp = await client.get(
            f"{_BASE}/{page}",
            params={"cmp_cd": symbol},
            headers={"User-Agent": _UA},
        )
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPError as exc:
        logger.warning("기업개요 페이지 조회 실패 %s/%s: %s", symbol, page, exc)
        return ""


async def get_company_overview(
    symbol: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """종목의 기업개요(개요·시세·주주현황·최근연혁·매출구성)를 반환한다.

    두 WiseReport 페이지를 동시 조회한다:
    - c1010001: 기업개요 불릿·시세·주주현황·기준일
    - c1020001: 최근연혁·주요제품 매출구성
    각 페이지는 독립적으로 graceful(실패 시 해당 항목만 빈 리스트).
    내용이 하나라도 있으면 종목별 하루 캐시 + 단일비행.
    """
    cached = _cache.get(symbol)
    if cached is not None and time.monotonic() - cached[0] < _OVERVIEW_TTL_SEC:
        return cached[1]

    lock = _locks.setdefault(symbol, asyncio.Lock())
    async with lock:
        cached = _cache.get(symbol)
        if cached is not None and time.monotonic() - cached[0] < _OVERVIEW_TTL_SEC:
            return cached[1]

        owns = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
        try:
            profile_html, detail_html = await asyncio.gather(
                _fetch_page(client, _PAGE_PROFILE, symbol),
                _fetch_page(client, _PAGE_DETAIL, symbol),
            )
        finally:
            if owns:
                await client.aclose()

        result = {"symbol": symbol, **_parse_profile(profile_html), **_parse_detail(detail_html)}
        # 내용이 하나라도 있을 때만 캐시(빈 결과/오류는 캐시하지 않아 다음 호출에서 재시도)
        if any(result[k] for k in ("summary", "price", "shareholders", "history", "products")):
            _cache[symbol] = (time.monotonic(), result)
        return result
