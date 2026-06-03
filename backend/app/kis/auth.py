"""KIS 접근토큰(access_token) 발급/캐시/갱신 클라이언트.

- 토큰 유효기간 24시간. 만료 60초 전부터 재발급.
- 6시간 이내 재요청 시 KIS가 기존 토큰을 반환하므로 메모리 캐시로 충분.
- 서버 재시작 시 토큰을 재발급하면 KIS가 잦은 발급을 throttle(403)하므로,
  토큰을 파일(`data/.kis_token_<mode>.json`)에 영속화해 재시작 시 재사용한다.
  (해당 파일은 시크릿이므로 `data/`로 gitignore된다.)
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx

from app.config import Settings, get_settings

_TOKEN_PATH = "/oauth2/tokenP"
_APPROVAL_PATH = "/oauth2/Approval"
_EXPIRY_MARGIN_SEC = 60


class KisAuth:
    """접근토큰 발급 + 메모리/파일 캐시."""

    def __init__(self, settings: Settings | None = None, mode: str | None = None) -> None:
        self._settings = settings or get_settings()
        self._mode = mode or self._settings.trading_mode
        self._creds = self._settings.kis_for(self._mode)
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()
        self._file_checked = False

    @property
    def _token_file(self) -> Path:
        parent = Path(self._settings.database_path).parent
        return parent / f".kis_token_{self._mode}.json"

    async def get_access_token(self, client: httpx.AsyncClient | None = None) -> str:
        """유효한 access_token을 반환한다. 메모리→파일→발급 순으로 재사용한다."""
        if self._is_valid():
            assert self._token is not None
            return self._token

        async with self._lock:
            if self._is_valid():
                assert self._token is not None
                return self._token
            # 최초 1회 파일 캐시 확인(재시작 후 재발급 방지)
            if not self._file_checked:
                self._file_checked = True
                self._load_file()
                if self._is_valid():
                    assert self._token is not None
                    return self._token
            return await self._fetch(client)

    def _is_valid(self) -> bool:
        return self._token is not None and time.time() < self._expires_at - _EXPIRY_MARGIN_SEC

    def _load_file(self) -> None:
        try:
            data = json.loads(self._token_file.read_text(encoding="utf-8"))
            self._token = data["token"]
            self._expires_at = float(data["expires_at"])
        except (OSError, ValueError, KeyError):
            self._token = None
            self._expires_at = 0.0

    def _save_file(self) -> None:
        try:
            self._token_file.parent.mkdir(parents=True, exist_ok=True)
            self._token_file.write_text(
                json.dumps({"token": self._token, "expires_at": self._expires_at}),
                encoding="utf-8",
            )
        except OSError:
            pass

    async def _fetch(self, client: httpx.AsyncClient | None) -> str:
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self._creds.rest_base, timeout=10.0)
        try:
            resp = await client.post(
                _TOKEN_PATH,
                json={
                    "grant_type": "client_credentials",
                    "appkey": self._creds.app_key,
                    "appsecret": self._creds.app_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            expires_in = int(data.get("expires_in", 86400))
            self._token = token
            self._expires_at = time.time() + expires_in
            self._save_file()
            return token
        finally:
            if owns_client:
                await client.aclose()

    def invalidate(self) -> None:
        """캐시된 토큰을 폐기한다(메모리 + 파일)."""
        self._token = None
        self._expires_at = 0.0
        try:
            self._token_file.unlink()
        except OSError:
            pass

    async def get_approval_key(self, client: httpx.AsyncClient | None = None) -> str:
        """웹소켓 접속키(approval_key)를 발급한다.

        주의: 요청 body 필드명이 `secretkey`다 (`appsecret` 아님).
        """
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(base_url=self._creds.rest_base, timeout=10.0)
        try:
            resp = await client.post(
                _APPROVAL_PATH,
                json={
                    "grant_type": "client_credentials",
                    "appkey": self._creds.app_key,
                    "secretkey": self._creds.app_secret,
                },
            )
            resp.raise_for_status()
            return resp.json()["approval_key"]
        finally:
            if owns_client:
                await client.aclose()
