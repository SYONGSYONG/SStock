"""대시보드 브로드캐스트 허브.

서버가 수신한 실시간 데이터를 연결된 모든 대시보드 클라이언트로 푸시한다.
클라이언트는 `async def send_text(str)` 를 가진 객체면 된다(FastAPI WebSocket 호환).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol


class WSClient(Protocol):
    async def send_text(self, data: str) -> None: ...


class DashboardHub:
    def __init__(self) -> None:
        self._clients: set[WSClient] = set()
        self._lock = asyncio.Lock()

    async def register(self, client: WSClient) -> None:
        async with self._lock:
            self._clients.add(client)

    async def unregister(self, client: WSClient) -> None:
        async with self._lock:
            self._clients.discard(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """모든 클라이언트에 JSON 메시지를 푸시한다. 실패한 클라이언트는 제거한다."""
        payload = json.dumps(message, ensure_ascii=False)
        async with self._lock:
            targets = list(self._clients)
        dead: list[WSClient] = []
        for client in targets:
            try:
                await client.send_text(payload)
            except Exception:  # noqa: BLE001 - 끊긴 클라이언트는 정리 대상
                dead.append(client)
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)


# 앱 전역 단일 허브
hub = DashboardHub()
