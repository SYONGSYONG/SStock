"""KIS 접근토큰(access_token) 발급/캐시/갱신 클라이언트.

- 토큰 유효기간 24시간. 만료 60초 전부터 재발급.
- 6시간 이내 재요청 시 KIS가 기존 토큰을 반환하므로 메모리 캐시로 충분.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.config import Settings, get_settings

_TOKEN_PATH = "/oauth2/tokenP"
_EXPIRY_MARGIN_SEC = 60


class KisAuth:
    """접근토큰 발급 및 메모리 캐시."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_access_token(self, client: httpx.AsyncClient | None = None) -> str:
        """유효한 access_token을 반환한다. 캐시가 유효하면 재사용한다."""
        if self._is_valid():
            assert self._token is not None
            return self._token

        async with self._lock:
            # 락 획득 대기 중 다른 코루틴이 갱신했을 수 있음
            if self._is_valid():
                assert self._token is not None
                return self._token
            return await self._fetch(client)

    def _is_valid(self) -> bool:
        return self._token is not None and time.time() < self._expires_at - _EXPIRY_MARGIN_SEC

    async def _fetch(self, client: httpx.AsyncClient | None) -> str:
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self._settings.rest_base, timeout=10.0)
        try:
            resp = await client.post(
                _TOKEN_PATH,
                json={
                    "grant_type": "client_credentials",
                    "appkey": self._settings.kis_app_key,
                    "appsecret": self._settings.kis_app_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            expires_in = int(data.get("expires_in", 86400))
            self._token = token
            self._expires_at = time.time() + expires_in
            return token
        finally:
            if owns_client:
                await client.aclose()

    def invalidate(self) -> None:
        """캐시된 토큰을 폐기한다(폐기 API 호출 후 등)."""
        self._token = None
        self._expires_at = 0.0
