from fastapi import APIRouter, Request

from app.schemas.response import ApiResponse, ok


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/startup", response_model=ApiResponse[dict[str, object]])
def startup_status(request: Request) -> ApiResponse[dict[str, object]]:
    return ok(getattr(request.app.state, "startup_checks", {}))
