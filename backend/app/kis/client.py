"""KIS REST API 공통 클라이언트.

인증 토큰 + 공통 헤더(appkey/appsecret/tr_id/custtype)를 구성해 호출한다.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.auth import KisAuth


class KisClient:
    def __init__(self, settings: Settings | None = None, auth: KisAuth | None = None) -> None:
        self._settings = settings or get_settings()
        self._auth = auth or KisAuth(self._settings)

    async def _headers(self, tr_id: str, client: httpx.AsyncClient) -> dict[str, str]:
        token = await self._auth.get_access_token(client)
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._settings.kis_app_key,
            "appsecret": self._settings.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    async def get(
        self,
        path: str,
        tr_id: str,
        params: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self._settings.rest_base, timeout=10.0)
        try:
            headers = await self._headers(tr_id, client)
            resp = await client.get(path, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()

    async def post(
        self,
        path: str,
        tr_id: str,
        body: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self._settings.rest_base, timeout=10.0)
        try:
            headers = await self._headers(tr_id, client)
            resp = await client.post(path, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()
        finally:
            if owns_client:
                await client.aclose()
