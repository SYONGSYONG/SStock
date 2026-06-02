"""KIS 접근토큰 발급/캐시 테스트 (HTTP는 respx로 mock)."""

from __future__ import annotations

import httpx
import respx

from app.config import Settings
from app.kis.auth import KisAuth


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        trading_mode="paper",
        kis_app_key="dummy_key",
        kis_app_secret="dummy_secret",
    )


@respx.mock
async def test_토큰_발급_성공():
    settings = _settings()
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "TOKEN_ABC", "expires_in": 86400, "token_type": "Bearer"},
        )
    )
    auth = KisAuth(settings)
    token = await auth.get_access_token()

    assert token == "TOKEN_ABC"
    assert route.call_count == 1


@respx.mock
async def test_토큰_캐시_재사용():
    settings = _settings()
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "TOKEN_ABC", "expires_in": 86400, "token_type": "Bearer"},
        )
    )
    auth = KisAuth(settings)
    first = await auth.get_access_token()
    second = await auth.get_access_token()

    assert first == second == "TOKEN_ABC"
    # 캐시가 유효하므로 HTTP 호출은 1회뿐
    assert route.call_count == 1


@respx.mock
async def test_토큰_폐기_후_재발급():
    settings = _settings()
    route = respx.post(f"{settings.rest_base}/oauth2/tokenP").mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "TOKEN_ABC", "expires_in": 86400, "token_type": "Bearer"},
        )
    )
    auth = KisAuth(settings)
    await auth.get_access_token()
    auth.invalidate()
    await auth.get_access_token()

    assert route.call_count == 2
