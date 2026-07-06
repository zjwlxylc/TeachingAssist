from fastapi import APIRouter, Depends, File, Form, UploadFile
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
