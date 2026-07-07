from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import messages as message_service
from app.services.auth import validate_token
from app.services.realtime import message_manager


router = APIRouter(prefix="/messages", tags=["messages"])
ws_router = APIRouter(tags=["websocket"])


class StudentMessageRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=message_service.MAX_MESSAGE_LENGTH)


class TeacherReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=message_service.MAX_MESSAGE_LENGTH)


@router.post("", response_model=ApiResponse[dict[str, object]])
async def student_send(payload: StudentMessageRequest) -> ApiResponse[dict[str, object]]:
    return ok(
        await message_service.send_student_message(payload.student_id, payload.name, payload.content),
        message="私信已发送",
    )


@router.get("/mine", response_model=ApiResponse[list[dict[str, object]]])
def student_thread(
    student_id: str = Query(min_length=1),
    name: str = Query(min_length=1),
) -> ApiResponse[list[dict[str, object]]]:
    pk = message_service.resolve_student_pk(student_id, name)
    return ok(message_service.get_student_thread(pk))


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
    # 私信通道必须鉴权：老师凭 token，学生凭 学号+姓名；否则立即关闭，杜绝裸连泄露。
    room: str | None = None
    try:
        if token:
            teacher = validate_token(token)
            if teacher is None:
                await websocket.close(code=4401)
                return
            room = "teacher"
        elif student_id and name:
            pk = message_service.resolve_student_pk(student_id, name)
            room = f"student:{pk}"
        else:
            await websocket.close(code=4400)
            return
    except Exception:
        await websocket.close(code=4401)
        return

    await message_manager.connect(room, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        message_manager.disconnect(room, websocket)
    except Exception:
        message_manager.disconnect(room, websocket)
