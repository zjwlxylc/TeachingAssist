from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import classroom as classroom_service


router = APIRouter(prefix="/classroom", tags=["classroom"])


class StudentSignInRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


@router.post("/sessions/{session_id}/start", response_model=ApiResponse[dict[str, object]])
def start_session(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(classroom_service.start_session(session_id), message="课堂已开始")


@router.post("/sessions/{session_id}/end", response_model=ApiResponse[dict[str, object]])
def end_session(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(classroom_service.end_session(session_id), message="课堂已结束")


@router.get("/sessions/active/list", response_model=ApiResponse[list[dict[str, object]]])
def active_sessions() -> ApiResponse[list[dict[str, object]]]:
    return ok(classroom_service.list_active_sessions())


@router.get("/sessions/{session_id}", response_model=ApiResponse[dict[str, object]])
def public_session(session_id: int) -> ApiResponse[dict[str, object]]:
    return ok(classroom_service.get_session_public(session_id))


@router.post("/sessions/{session_id}/sign-in", response_model=ApiResponse[dict[str, object]])
def student_sign_in(
    session_id: int,
    payload: StudentSignInRequest,
    request: Request,
) -> ApiResponse[dict[str, object]]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ok(
        classroom_service.student_sign_in(session_id, payload.student_id, payload.name, ip_address, user_agent),
        message="签到成功",
    )


@router.get("/sessions/{session_id}/sign-ins", response_model=ApiResponse[dict[str, object]])
def sign_in_summary(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(classroom_service.get_sign_in_summary(session_id))
