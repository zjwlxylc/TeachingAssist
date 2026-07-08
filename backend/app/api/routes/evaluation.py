from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import evaluation as evaluation_service


router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationCalculateRequest(BaseModel):
    version_type: str = "temporary"


class EvaluationWeightsRequest(BaseModel):
    attendance_weight: float = Field(ge=0)
    question_weight: float = Field(ge=0)
    homework_weight: float = Field(ge=0)
    message_weight: float = Field(ge=0)
    activity_weight: float = Field(ge=0)


class StudentFeedbackRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    token: str | None = None


@router.post("/sessions/{session_id}/calculate", response_model=ApiResponse[dict[str, object]])
def calculate_session(
    session_id: int,
    payload: EvaluationCalculateRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(evaluation_service.calculate_session(session_id, payload.version_type), message="学习效果评估已生成")


@router.get("/sessions/{session_id}", response_model=ApiResponse[dict[str, object]])
def session_report(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(evaluation_service.get_session_report(session_id))


@router.put("/weights", response_model=ApiResponse[dict[str, object]])
def update_weights(
    payload: EvaluationWeightsRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(evaluation_service.update_weights(payload.model_dump()), message="评估权重已保存")


@router.post("/sessions/{session_id}/student-feedback", response_model=ApiResponse[dict[str, object]])
def student_feedback(session_id: int, payload: StudentFeedbackRequest) -> ApiResponse[dict[str, object]]:
    return ok(evaluation_service.get_student_feedback(session_id, payload.student_id, payload.name, payload.token))


@router.get("/sessions/{session_id}.csv")
def export_session(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> Response:
    exported = evaluation_service.export_session(session_id)
    return Response(
        content=exported["content"],
        media_type=exported["content_type"],
        headers={"Content-Disposition": f"attachment; filename={exported['file_name']}"},
    )
