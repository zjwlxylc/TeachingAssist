from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import interactions as interaction_service


router = APIRouter(prefix="/interactions", tags=["interactions"])


class InteractionSettingsRequest(BaseModel):
    student_messages_enabled: bool


class TeacherMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=300)


class StudentMessageRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=300)


@router.get("/sessions/{session_id}/settings", response_model=ApiResponse[dict[str, object]])
def get_settings(session_id: int) -> ApiResponse[dict[str, object]]:
    return ok(interaction_service.get_settings(session_id))


@router.put("/sessions/{session_id}/settings", response_model=ApiResponse[dict[str, object]])
async def update_settings(
    session_id: int,
    payload: InteractionSettingsRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        await interaction_service.update_settings(session_id, payload.student_messages_enabled),
        message="课堂互动设置已更新",
    )


@router.get("/sessions/{session_id}/messages", response_model=ApiResponse[list[dict[str, object]]])
def list_messages(
    session_id: int,
    last_message_id: int | None = None,
) -> ApiResponse[list[dict[str, object]]]:
    return ok(interaction_service.list_messages(session_id, last_message_id))


@router.post("/sessions/{session_id}/messages/teacher", response_model=ApiResponse[dict[str, object]])
async def publish_teacher_message(
    session_id: int,
    payload: TeacherMessageRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        await interaction_service.publish_teacher_message(session_id, payload.content, str(teacher.get("name") or "教师")),
        message="课堂互动消息已发送",
    )


@router.post("/sessions/{session_id}/messages/student", response_model=ApiResponse[dict[str, object]])
async def publish_student_message(
    session_id: int,
    payload: StudentMessageRequest,
) -> ApiResponse[dict[str, object]]:
    return ok(
        await interaction_service.publish_student_message(session_id, payload.student_id, payload.name, payload.content),
        message="课堂互动消息已发送",
    )
