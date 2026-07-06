from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import recovery as recovery_service


router = APIRouter(prefix="/recovery", tags=["recovery"])


class InterruptionRequest(BaseModel):
    started_at: str
    ended_at: str
    details: dict[str, Any] = {}


class RecoveryActionRequest(BaseModel):
    event_id: int
    action: str


class CachedReplayRequest(BaseModel):
    payload: dict[str, Any] = {}


@router.post("/sessions/{session_id}/interruptions", response_model=ApiResponse[dict[str, object]])
def record_interruption(
    session_id: int,
    payload: InterruptionRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        recovery_service.record_interruption(session_id, payload.started_at, payload.ended_at, payload.details),
        message="中断事件已记录",
    )


@router.post("/sessions/{session_id}/actions", response_model=ApiResponse[dict[str, object]])
def apply_action(
    session_id: int,
    payload: RecoveryActionRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(
        recovery_service.apply_recovery_action(session_id, payload.event_id, payload.action),
        message="中断处理已应用",
    )


@router.post("/sessions/{session_id}/cached-replays", response_model=ApiResponse[dict[str, object]])
def cached_replay(session_id: int, payload: CachedReplayRequest) -> ApiResponse[dict[str, object]]:
    return ok(recovery_service.record_cached_replay(session_id, payload.payload), message="缓存请求已记录")


@router.get("/sessions/{session_id}/events", response_model=ApiResponse[list[dict[str, object]]])
def events(
    session_id: int,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[list[dict[str, object]]]:
    return ok(recovery_service.list_events(session_id))
