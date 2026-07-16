import asyncio

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import messages as message_service
from app.services.auth import validate_token
from app.services.realtime import WS_IDLE_TIMEOUT_SECONDS, message_manager


router = APIRouter(prefix="/messages", tags=["messages"])
ws_router = APIRouter(tags=["websocket"])


class StudentMessageRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=message_service.MAX_MESSAGE_LENGTH)
    token: str | None = None


class TeacherReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=message_service.MAX_MESSAGE_LENGTH)


@router.post("", response_model=ApiResponse[dict[str, object]])
async def student_send(payload: StudentMessageRequest) -> ApiResponse[dict[str, object]]:
    # token 优先：提供令牌时后端以令牌解析身份（防冒名）；否则退回学号+姓名
    return ok(
        await message_service.send_student_message(payload.student_id, payload.name, payload.content, payload.token),
        message="私信已发送",
    )


@router.get("/mine", response_model=ApiResponse[list[dict[str, object]]])
def student_thread(
    student_id: str = Query(min_length=1),
    name: str = Query(min_length=1),
    token: str | None = Query(default=None),
) -> ApiResponse[list[dict[str, object]]]:
    pk = message_service.resolve_student_pk_for_read(student_id, name, token)
    return ok(message_service.get_student_thread(pk))


@router.post("/mine/read", response_model=ApiResponse[dict[str, object]])
def student_mark_read(token: str | None = Query(default=None)) -> ApiResponse[dict[str, object]]:
    # 显式标记已读，避免 GET /messages/mine 内写库副作用
    updated = message_service.mark_student_messages_read(token)
    return ok({"updated": updated})


@router.post("/students/{student_id}/read", response_model=ApiResponse[dict[str, object]])
def teacher_mark_read(
    student_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    updated = message_service.mark_teacher_messages_read(student_id)
    return ok({"updated": updated})


@router.get("/conversations", response_model=ApiResponse[list[dict[str, object]]])
def teacher_conversations(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[list[dict[str, object]]]:
    return ok(message_service.list_conversations())


@router.get("/students/{student_id}", response_model=ApiResponse[dict[str, object]])
def teacher_thread(
    student_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(message_service.get_teacher_thread(student_id))


@router.post("/students/{student_id}/reply", response_model=ApiResponse[dict[str, object]])
async def teacher_reply(
    student_id: int,
    payload: TeacherReplyRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        await message_service.reply_to_student(student_id, str(teacher.get("name") or "教师"), payload.content),
        message="已回复",
    )


@router.get("/unread-count", response_model=ApiResponse[dict[str, object]])
def teacher_unread(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, object]]:
    return ok(message_service.get_unread_count())


@ws_router.websocket("/ws/messages")
async def messages_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    name: str | None = Query(default=None),
) -> None:
    # 私信通道必须鉴权：老师凭 token，学生凭 会话令牌（优先）或 学号+姓名；否则立即关闭，杜绝裸连泄露。
    room: str | None = None
    try:
        if token:
            teacher = validate_token(token)
            if teacher is not None:
                room = "teacher"
            else:
                # 非教师令牌：必须是有效的学生会话令牌，不再退回学号+姓名
                pk = message_service.verify_student_token(token)
                if pk is not None:
                    room = f"student:{pk}"
        if room is None:
            await websocket.close(code=4400)
            return
    except Exception:
        await websocket.close(code=4401)
        return

    await message_manager.connect(room, websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=WS_IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                # 空闲超时：主动关闭以释放长期“连而不发”的连接。
                break
    except WebSocketDisconnect:
        message_manager.disconnect(room, websocket)
    except Exception:
        message_manager.disconnect(room, websocket)
    finally:
        message_manager.disconnect(room, websocket)
