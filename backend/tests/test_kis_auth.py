"""KIS 접근토큰 발급/캐시 테스트 (HTTP는 respx로 mock).

토큰 파일 캐시가 실제 ./data 를 오염시키지 않도록 database_path를 tmp로 격리한다.
"""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.auth import KisAuth

_TOKEN_JSON = {"access_token": "TOKEN_ABC", "expires_in": 86400, "token_type": "Bearer"}


def _settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_paper_app_key="dummy_key",
        kis_paper_app_secret="dummy_secret",
        database_path=str(tmp_path / "sstock.db"),
    )


@respx.mock
async def test_토큰_발급_성공(tmp_path):
    settings = _settings(tmp_path)
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json=_TOKEN_JSON)
    )
    token = await KisAuth(settings).get_access_token()

    assert token == "TOKEN_ABC"
    assert route.call_count == 1


@respx.mock
async def test_토큰_캐시_재사용(tmp_path):
    settings = _settings(tmp_path)
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json=_TOKEN_JSON)
    )
    auth = KisAuth(settings)
    first = await auth.get_access_token()
    second = await auth.get_access_token()

    assert first == second == "TOKEN_ABC"
    assert route.call_count == 1


@respx.mock
async def test_토큰_폐기_후_재발급(tmp_path):
    settings = _settings(tmp_path)
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json=_TOKEN_JSON)
    )
    auth = KisAuth(settings)
    await auth.get_access_token()
    auth.invalidate()
    await auth.get_access_token()

    assert route.call_count == 2


@respx.mock
async def test_토큰_파일_재사용_재시작(tmp_path):
    """다른 KisAuth 인스턴스(재시작 모사)가 파일 캐시를 재사용한다."""
    settings = _settings(tmp_path)
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(200, json=_TOKEN_JSON)
    )
    first = await KisAuth(settings).get_access_token()
    # 새 인스턴스: 파일에서 로드 → 재발급 없음
    second = await KisAuth(settings).get_access_token()

    assert first == second == "TOKEN_ABC"
    assert route.call_count == 1
