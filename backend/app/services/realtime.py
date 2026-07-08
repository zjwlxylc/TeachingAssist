import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)

# 单条 send 的最长等待时间：个别卡死/慢速 socket 超过该时间即判定为失联并剔除，
# 避免 asyncio.gather 被单点拖住、拖累整组广播。
SEND_TIMEOUT_SECONDS = 5.0

# WebSocket 空闲超时：客户端长时间不发任何消息（包括心跳）即由服务端主动关闭，
# 释放被“连而不发”占用的连接资源。前端具备重连机制，断开后会自动恢复。
WS_IDLE_TIMEOUT_SECONDS = 300.0


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[object, set[WebSocket]] = defaultdict(set)

    async def connect(self, room: object, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[room].add(websocket)

    def disconnect(self, room: object, websocket: WebSocket) -> None:
        sockets = self._connections.get(room)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(room, None)

    async def broadcast(self, room: object, payload: dict[str, Any]) -> None:
        sockets = list(self._connections.get(room, set()))
        if not sockets:
            return
        message = json.dumps(payload, ensure_ascii=False)

        async def _safe_send(ws: WebSocket) -> WebSocket | None:
            try:
                await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_SECONDS)
                return None
            except Exception:
                return ws

        results = await asyncio.gather(*(_safe_send(ws) for ws in sockets))
        for stale_ws in results:
            if stale_ws is not None:
                self.disconnect(room, stale_ws)


manager = ConnectionManager()
# 私信专用连接管理器：按字符串 room 键分组（"teacher" 或 "student:{student_id}"），
# 与课堂广播通道 (manager) 物理隔离，保证私信内容不泄露给其他学生。
message_manager = ConnectionManager()
