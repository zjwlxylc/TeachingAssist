from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import homework as homework_service


router = APIRouter(prefix="/homework", tags=["homework"])


class HomeworkCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deadline: str
    grading_criteria: str | None = None
    allow_late: bool = False


class HomeworkReviewRequest(BaseModel):
    final_score: float = Field(ge=0)
    final_feedback: str | None = None


class HomeworkFeedbackRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


@router.post("/sessions/{session_id}", response_model=ApiResponse[dict[str, object]])
def create_homework(
    session_id: int,
    payload: HomeworkCreateRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.create_homework(session_id, payload.model_dump()), message="作业已发布")


@router.get("/sessions/{session_id}", response_model=ApiResponse[list[dict[str, object]]])
def list_homework(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(homework_service.list_homework(session_id))


@router.get("/sessions/{session_id}/public", response_model=ApiResponse[list[dict[str, object]]])
def public_homework(session_id: int) -> ApiResponse[list[dict[str, object]]]:
    return ok(homework_service.list_homework(session_id, public_only=True))


@router.post("/{homework_id}/submissions", response_model=ApiResponse[dict[str, object]])
def submit_homework(
    homework_id: int,
    student_id: str = Form(...),
    name: str = Form(...),
    text_content: str | None = Form(default=None),
    files: list[UploadFile] | None = File(default=None),
) -> ApiResponse[dict[str, object]]:
    return ok(
        homework_service.submit_homework(homework_id, student_id, name, text_content, files),
        message="作业已提交",
    )


@router.get("/{homework_id}/submissions", response_model=ApiResponse[dict[str, object]])
def submission_summary(
    homework_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.get_submission_summary(homework_id))


@router.post("/{homework_id}/attachments", response_model=ApiResponse[dict[str, object]])
def add_attachments(
    homework_id: int,
    files: list[UploadFile] | None = File(default=None),
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.add_homework_attachments(homework_id, files), message="作业附件已上传")


@router.post("/{homework_id}/ai-review", response_model=ApiResponse[dict[str, object]])
def start_ai_review(
    homework_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.start_ai_review(homework_id), message="AI 批阅任务已处理")


@router.put("/submissions/{submission_id}/review", response_model=ApiResponse[dict[str, object]])
def review_submission(
    submission_id: int,
    payload: HomeworkReviewRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        homework_service.review_submission(submission_id, payload.final_score, payload.final_feedback),
        message="教师复核结果已保存",
    )


@router.post("/{homework_id}/publish-grades", response_model=ApiResponse[dict[str, object]])
def publish_grades(
    homework_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.publish_homework_grades(homework_id), message="作业成绩已发布")


@router.post("/{homework_id}/feedback", response_model=ApiResponse[dict[str, object]])
def student_feedback(homework_id: int, payload: HomeworkFeedbackRequest) -> ApiResponse[dict[str, object]]:
    return ok(homework_service.get_student_homework_feedback(homework_id, payload.student_id, payload.name))


@router.get("/{homework_id}/submissions.csv")
def export_homework(
    homework_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> Response:
    exported = homework_service.export_homework(homework_id)
    return Response(
        content=exported["content"],
        media_type=exported["content_type"],
        headers={"Content-Disposition": f"attachment; filename={exported['file_name']}"},
    )
