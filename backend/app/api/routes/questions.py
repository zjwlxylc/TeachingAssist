from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import questions as question_service


router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionOptionRequest(BaseModel):
    option_key: str | None = None
    content: str = Field(min_length=1, max_length=500)
    is_correct: bool = False
    display_order: int | None = None


class QuestionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2000)
    question_type: str
    options: list[QuestionOptionRequest] = []
    correct_answer: Any = None
    keywords: list[str] = []
    score: float = Field(default=1, gt=0)
    start_time: str | None = None
    deadline: str | None = None


class AnswerSubmitRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    answer: Any = None
    action: str = "submit_answer"


@router.post("/sessions/{session_id}", response_model=ApiResponse[dict[str, object]])
async def create_question(
    session_id: int,
    payload: QuestionCreateRequest,
    teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        await question_service.create_question(session_id, payload.model_dump(), str(teacher.get("name") or "教师")),
        message="问题已发布",
    )


@router.get("/sessions/{session_id}", response_model=ApiResponse[list[dict[str, object]]])
def list_questions(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(question_service.list_questions(session_id, include_answer=True))


@router.get("/sessions/{session_id}/public", response_model=ApiResponse[list[dict[str, object]]])
def public_questions(session_id: int) -> ApiResponse[list[dict[str, object]]]:
    return ok(question_service.list_questions(session_id, include_answer=False, public_only=True))


@router.post("/{question_id}/answers", response_model=ApiResponse[dict[str, object]])
async def submit_answer(question_id: int, payload: AnswerSubmitRequest) -> ApiResponse[dict[str, object]]:
    return ok(
        await question_service.submit_answer(question_id, payload.student_id, payload.name, payload.answer, payload.action),
        message="答案已提交",
    )


@router.get("/{question_id}/stats", response_model=ApiResponse[dict[str, object]])
def question_stats(
    question_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_question_stats(question_id))
