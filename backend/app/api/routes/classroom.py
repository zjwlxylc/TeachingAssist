from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import classroom as classroom_service


router = APIRouter(prefix="/classroom", tags=["classroom"])


class StudentSignInRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    device_hash: str | None = None


class SignInStatusRequest(BaseModel):
    student_pk: int
    status: str
    reason: str | None = None


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
        classroom_service.student_sign_in(
            session_id,
            payload.student_id,
            payload.name,
            ip_address,
            user_agent,
            payload.device_hash,
        ),
        message="签到成功",
    )


@router.get("/sessions/{session_id}/sign-ins", response_model=ApiResponse[dict[str, object]])
def sign_in_summary(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(classroom_service.get_sign_in_summary(session_id))


@router.put("/sessions/{session_id}/sign-ins/status", response_model=ApiResponse[dict[str, object]])
def update_sign_in_status(
    session_id: int,
    payload: SignInStatusRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        classroom_service.update_sign_in_status(
            session_id,
            payload.student_pk,
            payload.status,
            payload.reason,
            str(teacher.get("name") or "教师"),
        ),
        message="签到状态已更新",
    )


@router.get("/sessions/{session_id}/sign-ins/logs", response_model=ApiResponse[list[dict[str, object]]])
def sign_in_logs(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(classroom_service.list_sign_in_change_logs(session_id))


@router.get("/sessions/{session_id}/sign-ins.csv")
def export_sign_ins(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> Response:
    exported = classroom_service.export_sign_ins(session_id)
    return Response(
        content=exported["content"],
        media_type=exported["content_type"],
        headers={"Content-Disposition": f"attachment; filename={exported['file_name']}"},
    )


class ReviewAlertRequest(BaseModel):
    notes: str | None = None


@router.get("/sessions/{session_id}/device-alerts", response_model=ApiResponse[list[dict[str, object]]])
def get_device_alerts(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(classroom_service.get_device_sharing_alerts(session_id))


@router.put("/device-alerts/{alert_id}/review", response_model=ApiResponse[dict[str, object]])
def review_device_alert(
    alert_id: int,
    payload: ReviewAlertRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        classroom_service.review_device_alert(
            alert_id,
            str(teacher.get("name") or "教师"),
            payload.notes,
        ),
        message="警告已审核",
    )
