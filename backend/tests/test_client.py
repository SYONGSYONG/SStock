"""KIS 공통 클라이언트(KisClient) 재시도 동작 테스트."""

from __future__ import annotations

import asyncio
import time

import httpx
import respx

from app.config import Settings
from app.kis.client import KisClient, reset_rate_limiter

_TEST_PATH = "/uapi/domestic-stock/v1/quotations/inquire-price"


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="00000000",
        database_path=str(tmp_path / "sstock.db"),
    )


def _token_mock(s: Settings) -> None:
    respx.post(f"{s.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json={"access_token": "T", "expires_in": 86400})
    )


@respx.mock
async def test_초당거래건수초과_EGW00201_재시도후_성공(tmp_path):
    """HTTP 200 + rt_cd!=0(EGW00201)은 상태코드로 안 드러나지만 본문을 보고 재시도한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    route = respx.get(f"{s.rest_base}{_TEST_PATH}").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"rt_cd": "1", "msg_cd": "EGW00201", "msg1": "초당 거래건수를 초과하였습니다."},
            ),
            httpx.Response(200, json={"rt_cd": "0", "output": {"stck_prpr": "70000"}}),
        ]
    )

    data = await KisClient(s).get(_TEST_PATH, "FHKST01010100", {"FID_INPUT_ISCD": "005930"})

    assert data["rt_cd"] == "0"
    assert route.call_count == 2


@respx.mock
async def test_초당거래건수초과_계속되면_마지막응답_반환(tmp_path):
    """재시도를 모두 소진해도 예외 없이 마지막 본문(rt_cd!=0)을 그대로 반환한다."""
    s = _settings(tmp_path)
    _token_mock(s)
    respx.get(f"{s.rest_base}{_TEST_PATH}").mock(
        return_value=httpx.Response(
            200,
            json={"rt_cd": "1", "msg_cd": "EGW00201", "msg1": "초당 거래건수를 초과하였습니다."},
        )
    )

    data = await KisClient(s).get(_TEST_PATH, "FHKST01010100", {"FID_INPUT_ISCD": "005930"})

    assert data["msg_cd"] == "EGW00201"


@respx.mock
async def test_레이트리미터_호출간_최소간격_강제(tmp_path):
    """min_interval을 설정하면 동시 호출도 간격을 두고 흘려보낸다(EGW00201 사전 억제)."""
    s = Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="k",
        kis_app_secret="s",
        kis_account_no="00000000",
        database_path=str(tmp_path / "sstock.db"),
        kis_min_call_interval_sec=0.1,
    )
    assert s.kis_call_interval == 0.1
    _token_mock(s)
    respx.get(f"{s.rest_base}{_TEST_PATH}").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output": {}})
    )

    reset_rate_limiter()
    client = KisClient(s)
    start = time.monotonic()
    # 3건 동시 요청 → 슬롯이 0, 0.1, 0.2초로 배정되어 마지막은 ~0.2초 후 시작
    await asyncio.gather(
        *[client.get(_TEST_PATH, "FHKST01010100", {"FID_INPUT_ISCD": "005930"}) for _ in range(3)]
    )
    elapsed = time.monotonic() - start

    assert elapsed >= 0.2  # 최소 (3-1)*0.1 간격 강제
    reset_rate_limiter()


@respx.mock
async def test_모드별_자격증명과_도메인_분리(tmp_path):
    """KisClient(mode=...)는 해당 모드의 앱키로 해당 모드 도메인에 호출한다."""
    s = Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="pkey",
        kis_paper_app_secret="ps",
        kis_paper_account_no="11111111",
        kis_live_app_key="lkey",
        kis_live_app_secret="ls",
        kis_live_account_no="63376776",
        database_path=str(tmp_path / "sstock.db"),
    )
    p = s.kis_for("paper")
    live = s.kis_for("live")
    assert p.rest_base != live.rest_base
    for base, tok in ((p.rest_base, "PT"), (live.rest_base, "LT")):
        respx.post(f"{base}/oauth2/tokenP").mock(
            return_value=httpx.Response(200, json={"access_token": tok, "expires_in": 86400})
        )
    p_route = respx.get(f"{p.rest_base}{_TEST_PATH}").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output": {}})
    )
    l_route = respx.get(f"{live.rest_base}{_TEST_PATH}").mock(
        return_value=httpx.Response(200, json={"rt_cd": "0", "output": {}})
    )

    await KisClient(s, mode="paper").get(_TEST_PATH, "FHKST01010100", {"FID_INPUT_ISCD": "005930"})
    await KisClient(s, mode="live").get(_TEST_PATH, "FHKST01010100", {"FID_INPUT_ISCD": "005930"})

    assert p_route.calls.last.request.headers["appkey"] == "pkey"
    assert l_route.calls.last.request.headers["appkey"] == "lkey"


async def test_레이트리미터_모드는_서로_throttle하지_않는다():
    """한 모드의 슬롯이 밀려도 다른 모드 첫 호출은 즉시 통과(독립 리미터)."""
    from app.kis.client import _rate_gate

    reset_rate_limiter()
    await _rate_gate(0.2, "paper")  # paper 슬롯을 +0.2로 밀어둠
    start = time.monotonic()
    await _rate_gate(0.2, "live")  # live 첫 호출 → paper와 무관하게 대기 없음
    assert time.monotonic() - start < 0.05
    reset_rate_limiter()
