from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import ai as ai_service


router = APIRouter(prefix="/ai", tags=["ai"])


class ProviderRequest(BaseModel):
    provider_name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    api_key: str | None = None
    http_proxy: str | None = None
    enabled: bool = False
    clear_api_key: bool = False


class ConnectivityRequest(BaseModel):
    provider_id: int | None = None


class SafetySettingsRequest(BaseModel):
    max_length: int = 2000
    blocked_keywords: list[str] = Field(default_factory=list)
    keyword_action: str = "replace"
    display_strategy: str = "review_first"


class SafetyCheckRequest(BaseModel):
    text: str
    source_type: str = "manual_test"
    source_id: int | None = None


class FailureTaskRequest(BaseModel):
    scenario: str
    source_type: str | None = None
    source_id: int | None = None
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/overview", response_model=ApiResponse[dict[str, Any]])
def overview(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.get_ai_overview())


@router.post("/providers", response_model=ApiResponse[dict[str, Any]])
def create_provider(
    payload: ProviderRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.save_provider(payload.model_dump()), message="AI Provider 已保存")


@router.put("/providers/{provider_id}", response_model=ApiResponse[dict[str, Any]])
def update_provider(
    provider_id: int,
    payload: ProviderRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.save_provider(payload.model_dump(), provider_id), message="AI Provider 已保存")


@router.post("/providers/{provider_id}/activate", response_model=ApiResponse[dict[str, Any]])
def activate_provider(
    provider_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.activate_provider(provider_id), message="AI Provider 已切换")


@router.post("/check", response_model=ApiResponse[dict[str, Any]])
def check_connectivity(
    payload: ConnectivityRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.check_connectivity(payload.provider_id), message="AI 自检已完成")


@router.put("/safety", response_model=ApiResponse[dict[str, Any]])
def update_safety(
    payload: SafetySettingsRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(ai_service.update_safety_settings(payload.model_dump()), message="AI 内容安全策略已保存")


@router.post("/safety/check", response_model=ApiResponse[dict[str, Any]])
def check_safety(
    payload: SafetyCheckRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(
        ai_service.check_content_safety(payload.text, payload.source_type, payload.source_id),
        message="内容安全检查已完成",
    )


@router.get("/failure-tasks", response_model=ApiResponse[list[dict[str, Any]]])
def failure_tasks(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[list[dict[str, Any]]]:
    return ok(ai_service.list_failure_tasks())


@router.post("/failure-tasks", response_model=ApiResponse[dict[str, Any]])
def create_failure_task(
    payload: FailureTaskRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, Any]]:
    return ok(
        ai_service.record_failure_task(
            payload.scenario,
            payload.source_type,
            payload.source_id,
            payload.reason,
            payload.payload,
        ),
        message="AI 降级任务已记录",
    )
