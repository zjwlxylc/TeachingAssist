import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(session_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: int, payload: dict[str, Any]) -> None:
        sockets = list(self._connections.get(session_id, set()))
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
                self.disconnect(session_id, stale_ws)


manager = ConnectionManager()
