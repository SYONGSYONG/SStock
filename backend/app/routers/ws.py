"""대시보드 실시간 WebSocket 라우터."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.hub import hub

router = APIRouter()


@router.websocket("/ws/quotes")
async def ws_quotes(websocket: WebSocket) -> None:
    await websocket.accept()
    await hub.register(websocket)
    try:
        while True:
            # 클라이언트 메시지는 keepalive 용도로만 수신(현재 미사용)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(websocket)
