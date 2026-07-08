import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import announcements as announcement_service
from app.services.realtime import WS_IDLE_TIMEOUT_SECONDS, manager


router = APIRouter(prefix="/announcements", tags=["announcements"])
ws_router = APIRouter(tags=["websocket"])


class AnnouncementRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


@router.get("/sessions/{session_id}", response_model=ApiResponse[list[dict[str, object]]])
def list_announcements(
    session_id: int,
    last_message_id: int | None = None,
) -> ApiResponse[list[dict[str, object]]]:
    return ok(announcement_service.list_announcements(session_id, last_message_id))


@router.post("/sessions/{session_id}", response_model=ApiResponse[dict[str, object]])
async def publish_announcement(
    session_id: int,
    payload: AnnouncementRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    sender_name = str(teacher.get("name") or "教师")
    return ok(
        await announcement_service.publish_announcement(session_id, payload.content, sender_name),
        message="公告已发布",
    )


@ws_router.websocket("/ws/classroom/{session_id}")
async def classroom_websocket(websocket: WebSocket, session_id: int) -> None:
    await manager.connect(session_id, websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=WS_IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                # 空闲超时：主动关闭以释放长期“连而不发”的连接。
                break
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception:
        manager.disconnect(session_id, websocket)
    finally:
        manager.disconnect(session_id, websocket)
