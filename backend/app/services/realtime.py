import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


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
                await ws.send_text(message)
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
