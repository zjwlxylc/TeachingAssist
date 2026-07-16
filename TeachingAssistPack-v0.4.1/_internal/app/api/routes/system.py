from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services.backup import create_backup, list_backups, restore_backup
from app.services.network import get_access_info, save_selected_access


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/startup", response_model=ApiResponse[dict[str, object]])
def startup_status(request: Request) -> ApiResponse[dict[str, object]]:
    return ok(getattr(request.app.state, "startup_checks", {}))


class AccessInfoRequest(BaseModel):
    selected_ip: str | None = None
    selected_port: int | None = None


class RestoreBackupRequest(BaseModel):
    file_path: str


@router.get("/access", response_model=ApiResponse[dict[str, object]])
def access_info(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, object]]:
    return ok(get_access_info())


@router.post("/access", response_model=ApiResponse[dict[str, object]])
def update_access_info(
    payload: AccessInfoRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    # 持久化教师选择的访问配置，避免下次进入时丢失。
    save_selected_access(payload.selected_ip, payload.selected_port)
    return ok(get_access_info(payload.selected_ip, payload.selected_port))


@router.get("/backups", response_model=ApiResponse[list[dict[str, object]]])
def backups(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[list[dict[str, object]]]:
    return ok(list_backups())


@router.post("/backups", response_model=ApiResponse[list[dict[str, object]]])
def backup_now(_teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[list[dict[str, object]]]:
    return ok(create_backup("manual"), message="备份已完成")


@router.post("/backups/restore", response_model=ApiResponse[dict[str, object]])
def restore(
    payload: RestoreBackupRequest,
    _teacher: dict[str, object] = Depends(require_teacher),
) -> ApiResponse[dict[str, object]]:
    return ok(restore_backup(payload.file_path), message="备份已恢复")
