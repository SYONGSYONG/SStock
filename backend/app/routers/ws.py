"""대시보드 실시간 WebSocket 라우터."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.hub import hub

router = APIRouter()

# 클라이언트가 이 시간 동안 아무 메시지(keepalive 핑 포함)도 보내지 않으면 죽은 연결로
# 간주하고 정리한다. 프론트는 25초마다 핑을 보내므로 정상 연결은 타임아웃되지 않는다.
# half-open(정상 종료 없이 사라진) 연결은 WebSocketDisconnect가 영영 안 떠서 누적되는데,
# 이 수신 타임아웃이 이를 ~60초 내에 정리한다.
RECV_TIMEOUT_SEC = 60.0


@router.websocket("/ws/quotes")
async def ws_quotes(websocket: WebSocket) -> None:
    await websocket.accept()
    await hub.register(websocket)
    try:
        while True:
            try:
                # 클라이언트 메시지는 keepalive 용도(내용 미사용). 일정 시간 무신호면
                # 죽은 연결로 보고 종료 → finally에서 정리.
                await asyncio.wait_for(websocket.receive_text(), timeout=RECV_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(websocket)
