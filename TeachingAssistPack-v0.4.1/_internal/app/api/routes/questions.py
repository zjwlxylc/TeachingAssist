from typing import Any

from fastapi import APIRouter, Depends, Response
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


class DraftQueryRequest(BaseModel):
    student_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    token: str | None = None


class BonusSettingsRequest(BaseModel):
    participation_score: float = 1
    correct_score: float = 2
    timeliness_score: float = 0.5
    timeliness_percent: float = 30
    max_quality_score: float = 3
    session_cap: float = 20


class QualityScoreRequest(BaseModel):
    quality_score: int = Field(ge=0, le=3)


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


@router.get("/{question_id}/stats/anonymous", response_model=ApiResponse[dict[str, object]])
def anonymous_question_stats(
    question_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_anonymous_question_stats(question_id))


@router.post("/{question_id}/draft", response_model=ApiResponse[dict[str, object]])
def student_draft(question_id: int, payload: DraftQueryRequest) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_student_draft(question_id, payload.student_id, payload.name, payload.token))


@router.get("/sessions/{session_id}/my-answers", response_model=ApiResponse[dict[str, object]])
def my_answers(
    session_id: int,
    student_id: str,
    name: str,
    token: str | None = None,
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_student_answer_summary(session_id, student_id, name, token))


@router.get("/sessions/{session_id}/answers.csv")
def export_answers(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> Response:
    exported = question_service.export_question_answers(session_id)
    return Response(
        content=exported["content"],
        media_type=exported["content_type"],
        headers={"Content-Disposition": f"attachment; filename={exported['file_name']}"},
    )


@router.get("/sessions/{session_id}/bonus", response_model=ApiResponse[dict[str, object]])
def bonus_summary(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_session_bonus_summary(session_id))


@router.get("/bonus/settings", response_model=ApiResponse[dict[str, object]])
def bonus_settings(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_bonus_settings())


@router.put("/bonus/settings", response_model=ApiResponse[dict[str, object]])
def update_bonus_settings(
    payload: BonusSettingsRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.update_bonus_settings(payload.model_dump()), message="加分规则已保存")


@router.get("/{question_id}/answers", response_model=ApiResponse[dict[str, object]])
def question_answers_detail(
    question_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(question_service.get_question_answers_detail(question_id))


@router.put("/answers/{answer_id}/quality-score", response_model=ApiResponse[dict[str, object]])
def set_quality_score(
    answer_id: int,
    payload: QualityScoreRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    teacher = _teacher
    result = question_service.set_answer_quality_score(answer_id, payload.quality_score)
    return ok(result, message="质量分已更新")
