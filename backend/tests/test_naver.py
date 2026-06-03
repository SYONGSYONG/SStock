"""기업개요 스크래핑(WiseReport) 테스트 (respx mock).

두 페이지를 조회한다: c1010001(개요·시세·주주), c1020001(연혁·매출구성).
"""

from __future__ import annotations

import httpx
import respx

from app.stocks import naver

_URL_PROFILE = "https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx"
_URL_DETAIL = "https://navercomp.wisereport.co.kr/v2/company/c1020001.aspx"

# c1010001: 기업개요 불릿 + 시세(cTB11) + 주주(p_sJJ)
_SAMPLE_PROFILE = """
<h5><span>기업개요</span></h5>
<p>[기준:2026.06.02]</p>
<div class="cmp_comment"><ul class="dot_cmp">
<li class="dot_cmp" data-cd="005930">동사는 1969년 설립된 글로벌 전자 기업.</li>
<li class="dot_cmp" data-cd="005930">DX는 가전, DS는 반도체 사업 운영.</li>
</ul></div>
<table id="cTB11"><tbody>
<tr><th>시가총액</th><td>21,075,834억원</td></tr>
<tr><th>외국인지분율</th><td>48.30%</td></tr>
</tbody></table>
<table><tbody>
<tr class="p_sJJ10">
  <td class="line txt" title="삼성생명보험 외 15인"><span>삼성생명보험 외 15인</span></td>
  <td class="line num">1,151,513,080&nbsp;</td>
  <td class="noli num">19.70&nbsp;</td>
</tr>
</tbody></table>
"""

# c1020001: 최근연혁(cTB202) + 주요제품 매출구성(cTB203)
_SAMPLE_DETAIL = """
<table id="cTB202"><thead><tr><th>일자</th><th class="blind-td">상세연혁</th></tr></thead><tbody>
<tr><th scope="row" class="c1 center ">2025/12</th>
    <td class="txt " title="6세대 D램 양산"><span class="cut">6세대 D램 양산</span></td></tr>
</tbody></table>
<table id="cTB203"><thead><tr><th>제품명</th><th class="blind-td">구성비</th></tr></thead><tbody>
<tr><th scope="row" class="c1 txt " title="DS"><span class="cut">DS</span></th><td class="c2 num ">61.04</td></tr>
<tr><th scope="row" class="c1 txt " title="DX"><span class="cut">DX</span></th><td class="c2 num ">39.33</td></tr>
</tbody></table>
"""


def _mock(profile: str = "", detail: str = "", status: int = 200) -> None:
    respx.get(_URL_PROFILE).mock(return_value=httpx.Response(status, text=profile))
    respx.get(_URL_DETAIL).mock(return_value=httpx.Response(status, text=detail))


@respx.mock
async def test_기업개요_시세_주주현황_파싱():
    naver.clear_overview_cache()
    _mock(profile=_SAMPLE_PROFILE)

    r = await naver.get_company_overview("005930")

    assert r["symbol"] == "005930"
    assert r["base_date"] == "2026.06.02"
    assert len(r["summary"]) == 2
    assert "1969년 설립" in r["summary"][0]
    labels = {p["label"]: p["value"] for p in r["price"]}
    assert labels["시가총액"] == "21,075,834억원"
    assert len(r["shareholders"]) == 1
    assert r["shareholders"][0]["name"] == "삼성생명보험 외 15인"
    assert r["shareholders"][0]["shares"] == "1,151,513,080"
    assert r["shareholders"][0]["pct"] == "19.70"
    naver.clear_overview_cache()


@respx.mock
async def test_최근연혁_매출구성_파싱():
    naver.clear_overview_cache()
    _mock(profile=_SAMPLE_PROFILE, detail=_SAMPLE_DETAIL)

    r = await naver.get_company_overview("005930")

    assert len(r["history"]) == 1
    assert r["history"][0]["date"] == "2025/12"
    assert r["history"][0]["detail"] == "6세대 D램 양산"
    assert len(r["products"]) == 2
    assert r["products"][0] == {"name": "DS", "pct": "61.04"}
    assert r["products"][1] == {"name": "DX", "pct": "39.33"}
    naver.clear_overview_cache()


@respx.mock
async def test_기업개요_HTTP오류시_빈결과():
    naver.clear_overview_cache()
    _mock(status=500, profile="error", detail="error")

    r = await naver.get_company_overview("005930")

    assert r["symbol"] == "005930"
    assert r["summary"] == []
    assert r["price"] == []
    assert r["history"] == []
    naver.clear_overview_cache()


@respx.mock
async def test_기업개요_캐시_재호출_안함():
    naver.clear_overview_cache()
    profile_route = respx.get(_URL_PROFILE).mock(
        return_value=httpx.Response(200, text=_SAMPLE_PROFILE)
    )
    respx.get(_URL_DETAIL).mock(return_value=httpx.Response(200, text=_SAMPLE_DETAIL))

    await naver.get_company_overview("005930")
    await naver.get_company_overview("005930")

    assert profile_route.call_count == 1  # 두 번째는 캐시
    naver.clear_overview_cache()
