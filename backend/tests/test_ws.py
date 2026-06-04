"""대시보드 WebSocket 라우터 테스트(죽은 연결 정리)."""

from __future__ import annotations

import asyncio

from app.realtime.hub import hub
from app.routers import ws


class _SilentWS:
    """아무 메시지도 보내지 않는(=무신호) 가짜 WebSocket → 수신 타임아웃 유도."""

    def __init__(self) -> None:
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        await asyncio.sleep(10)  # 클라이언트가 영영 아무것도 안 보냄
        return "x"


async def test_무신호_연결은_타임아웃으로_정리(monkeypatch):
    monkeypatch.setattr(ws, "RECV_TIMEOUT_SEC", 0.02)
    before = hub.client_count
    sock = _SilentWS()

    await ws.ws_quotes(sock)  # 타임아웃 → 정리 후 반환

    assert sock.accepted is True
    # 등록 후 타임아웃으로 다시 정리되어 연결 수가 원상복귀
    assert hub.client_count == before
