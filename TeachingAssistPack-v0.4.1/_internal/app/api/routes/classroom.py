from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import classroom as classroom_service
from app.services import enrollment as enrollment_service


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


# ============ 学生注册申请 ============

class EnrollmentApplicationRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    major: str | None = None
    college: str | None = None
    grade: str | None = None
    device_hash: str | None = None


class ApproveApplicationRequest(BaseModel):
    class_id: int
    auto_sign_in: bool = True


class RejectApplicationRequest(BaseModel):
    rejection_reason: str | None = None


@router.post("/sessions/{session_id}/enrollment/apply", response_model=ApiResponse[dict[str, object]])
async def create_enrollment_application(
    session_id: int,
    payload: EnrollmentApplicationRequest,
    request: Request,
) -> ApiResponse[dict[str, object]]:
    """学生提交注册申请（公开接口）"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    result = await enrollment_service.create_application(
        session_id,
        payload.student_id,
        payload.name,
        payload.major,
        payload.college,
        payload.grade,
        ip_address,
        user_agent,
        payload.device_hash,
    )
    if result.get("status") == "auto_merged":
        return ok(result, message="已自动加入课堂名单，请重新签到")
    else:
        return ok(result, message="注册申请已提交，请等待教师审批")


@router.get("/sessions/{session_id}/enrollment/applications", response_model=ApiResponse[list[dict[str, object]]])
def list_enrollment_applications(
    session_id: int,
    status: str | None = None,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    """教师查看注册申请列表"""
    return ok(enrollment_service.list_applications(session_id, status))


@router.get("/sessions/{session_id}/enrollment/classes", response_model=ApiResponse[list[dict[str, object]]])
def get_session_classes(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    """获取课堂关联的班级列表（用于审批时选择）"""
    return ok(enrollment_service.get_session_classes(session_id))


@router.post("/sessions/{session_id}/enrollment/applications/{application_id}/approve", response_model=ApiResponse[dict[str, object]])
def approve_enrollment_application(
    session_id: int,
    application_id: int,
    payload: ApproveApplicationRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    """教师批准注册申请"""
    result = enrollment_service.approve_application(
        application_id,
        payload.class_id,
        payload.auto_sign_in,
        str(teacher.get("name") or "教师"),
    )
    message = "申请已批准"
    if result.get("auto_signed_in"):
        message += "，并已自动完成签到"
    else:
        message += "，学生已加入课堂名单"
    return ok(result, message=message)


@router.post("/sessions/{session_id}/enrollment/applications/{application_id}/reject", response_model=ApiResponse[dict[str, object]])
def reject_enrollment_application(
    session_id: int,
    application_id: int,
    payload: RejectApplicationRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    """教师拒绝注册申请"""
    return ok(
        enrollment_service.reject_application(
            application_id,
            payload.rejection_reason,
            str(teacher.get("name") or "教师"),
        ),
        message="申请已拒绝",
    )


@router.get("/enrollment/pending", response_model=ApiResponse[list[dict[str, object]]])
def list_pending_enrollment_applications(
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    """教师查看全部课堂的待审批注册申请（跨课堂汇总）"""
    return ok(enrollment_service.list_pending())
