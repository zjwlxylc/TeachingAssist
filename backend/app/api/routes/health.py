from fastapi import APIRouter

from app.core.config import get_settings
from app.db.migrations import integrity_check
from app.schemas.response import ApiResponse, ok


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=ApiResponse[dict[str, object]])
def health_check() -> ApiResponse[dict[str, object]]:
    settings = get_settings()
    return ok(
        {
            "status": "ok",
            "app_name": settings.app_name,
            "environment": settings.environment,
            "database_path": str(settings.storage.database_path),
            "database_integrity": integrity_check(),
        }
    )
