"""KIS REST API 공통 클라이언트.

인증 토큰 + 공통 헤더(appkey/appsecret/tr_id/custtype)를 구성해 호출한다.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.kis.auth import KisAuth

logger = logging.getLogger(__name__)

# KIS API TPS 제한을 고려하여 전역 동시 호출 수 제한 (기본 3)
_GLOBAL_SEMAPHORE = asyncio.Semaphore(3)

# KIS 초당 거래건수 초과는 HTTP 200 + 본문 rt_cd!="0" + msg_cd로 통지된다.
# HTTP 상태코드로는 드러나지 않으므로 본문을 검사해 별도로 재시도한다.
_RATE_LIMIT_MSG_CODES = frozenset({"EGW00201"})

# 모드별 레이트리미터: 모의(≈2/s)·실전(≈20/s)은 한도가 달라 슬롯을 분리한다.
# 한쪽 모드의 호출 폭주가 다른 모드 호출을 throttle하지 않게 한다.
_RATE_LOCK = asyncio.Lock()
_next_slot_by_mode: dict[str, float] = {}

# 앱 lifespan이 모드별로 등록하는 keep-alive 공유 httpx 클라이언트.
# 모의/실전은 도메인이 달라(rest_base) 모드별로 분리한다. 요청마다 새 클라이언트를
# 만들면 매번 TCP+TLS 핸드셰이크가 발생하므로 등록된 것을 재사용한다.
# 테스트(lifespan 미실행)에서는 비어 있어 요청별 클라이언트를 생성한다.
_shared_clients: dict[str, httpx.AsyncClient] = {}


def set_shared_client(mode: str, client: httpx.AsyncClient | None) -> None:
    """모드별 공유 httpx 클라이언트를 등록/해제한다(앱 lifespan에서 호출)."""
    if client is None:
        _shared_clients.pop(mode, None)
    else:
        _shared_clients[mode] = client


def get_shared_client(mode: str) -> httpx.AsyncClient | None:
    return _shared_clients.get(mode)


def reset_rate_limiter() -> None:
    """레이트리미터 슬롯을 초기화한다(테스트용)."""
    _next_slot_by_mode.clear()


async def _rate_gate(min_interval: float, mode: str) -> None:
    """모드별 호출 간 최소 간격을 강제한다(min_interval<=0이면 무시)."""
    if min_interval <= 0:
        return
    async with _RATE_LOCK:
        now = time.monotonic()
        prev = _next_slot_by_mode.get(mode, 0.0)
        slot = now if now > prev else prev
        _next_slot_by_mode[mode] = slot + min_interval
        wait = slot - now
    if wait > 0:
        await asyncio.sleep(wait)


class KisClient:
    def __init__(
        self,
        settings: Settings | None = None,
        auth: KisAuth | None = None,
        mode: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._mode = mode or self._settings.trading_mode
        self._creds = self._settings.kis_for(self._mode)
        self._auth = auth or KisAuth(self._settings, mode=self._mode)

    async def _headers(self, tr_id: str, client: httpx.AsyncClient) -> dict[str, str]:
        token = await self._auth.get_access_token(client)
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self._creds.app_key,
            "appsecret": self._creds.app_secret,
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
        return await self._request("GET", path, tr_id, params=params, client=client)

    async def post(
        self,
        path: str,
        tr_id: str,
        body: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, tr_id, json=body, client=client)

    async def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        owns_client = False
        if client is None:
            client = _shared_clients.get(self._mode)  # 모드별 공유 클라이언트 우선
        if client is None:
            client = httpx.AsyncClient(base_url=self._creds.rest_base, timeout=10.0)
            owns_client = True

        max_retries = 3
        last_exc = None

        try:
            async with _GLOBAL_SEMAPHORE:
                for attempt in range(max_retries):
                    try:
                        # 1차 시도 (또는 재시도)
                        headers = await self._headers(tr_id, client)
                        await _rate_gate(self._creds.call_interval, self._mode)
                        resp = await client.request(method, path, headers=headers, params=params, json=json)

                        # 401(Unauthorized)이면 토큰 만료/오류 가능성 -> 무효화 후 즉시 재시도 (최대 1회)
                        if resp.status_code == 401:
                            self._auth.invalidate()
                            headers = await self._headers(tr_id, client)
                            await _rate_gate(self._creds.call_interval, self._mode)
                            resp = await client.request(method, path, headers=headers, params=params, json=json)

                        # TPS 제한(429, 503) 또는 일시적 오류인 경우 지수 백오프 후 재시도
                        if resp.status_code in (429, 503) and attempt < max_retries - 1:
                            delay = 0.5 * (2**attempt)  # 0.5s, 1s, 2s
                            logger.warning(
                                "KIS API 제한/지연 발생(HTTP %d), %0.1fs 후 재시도 (%d/%d)",
                                resp.status_code,
                                delay,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(delay)
                            continue

                        resp.raise_for_status()
                        data = resp.json()

                        # 초당 거래건수 초과(EGW00201)는 HTTP 200으로 와서 위 상태코드
                        # 재시도에 걸리지 않는다. 본문을 검사해 지수 백오프 후 재시도.
                        if (
                            data.get("rt_cd") not in (None, "0")
                            and data.get("msg_cd") in _RATE_LIMIT_MSG_CODES
                            and attempt < max_retries - 1
                        ):
                            delay = 0.5 * (2**attempt)  # 0.5s, 1s, 2s
                            logger.warning(
                                "KIS 초당 거래건수 초과(%s), %0.1fs 후 재시도 (%d/%d)",
                                data.get("msg_cd"),
                                delay,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(delay)
                            continue

                        return data

                    except (httpx.HTTPStatusError, httpx.NetworkError) as exc:
                        last_exc = exc
                        # 5xx 오류나 네트워크 오류인 경우 재시도 고려
                        status_code = getattr(exc.response, "status_code", None)
                        if (status_code and status_code >= 500 or isinstance(exc, httpx.NetworkError)) and attempt < max_retries - 1:
                            delay = 0.5 * (2**attempt)
                            logger.warning(
                                "KIS API 네트워크/서버 오류(%s), %0.1fs 후 재시도 (%d/%d)",
                                exc,
                                delay,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(delay)
                            continue
                        raise exc

                if last_exc:
                    raise last_exc
                raise httpx.HTTPError("최대 재시도 횟수 초과")
        finally:
            if owns_client:
                await client.aclose()
