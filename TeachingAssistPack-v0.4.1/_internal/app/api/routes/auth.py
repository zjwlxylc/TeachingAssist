from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import require_teacher
from app.schemas.response import ApiResponse, ok
from app.services import auth as auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


class SetupPasswordRequest(BaseModel):
    password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


@router.get("/status", response_model=ApiResponse[dict[str, object]])
def auth_status() -> ApiResponse[dict[str, object]]:
    return ok(auth_service.get_auth_status())


@router.post("/setup", response_model=ApiResponse[dict[str, object]])
def setup_password(payload: SetupPasswordRequest) -> ApiResponse[dict[str, object]]:
    token_info = auth_service.setup_teacher_password(payload.password, payload.confirm_password)
    return ok(token_info, message="教师密码已设置")


@router.post("/login", response_model=ApiResponse[dict[str, object]])
def login(payload: LoginRequest) -> ApiResponse[dict[str, object]]:
    token_info = auth_service.login_teacher(payload.password)
    return ok(token_info, message="登录成功")


@router.post("/logout", response_model=ApiResponse[dict[str, object]])
def logout(teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, object]]:
    auth_service.revoke_teacher_tokens(int(teacher["id"]))
    return ok({"logged_out": True}, message="已退出登录")


@router.get("/me", response_model=ApiResponse[dict[str, object]])
def me(teacher: dict[str, object] = Depends(require_teacher)) -> ApiResponse[dict[str, object]]:
    return ok(teacher)
