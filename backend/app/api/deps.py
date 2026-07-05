from fastapi import Header

from app.core.exceptions import AppError
from app.services.auth import validate_token


def require_teacher(authorization: str | None = Header(default=None)) -> dict[str, object]:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("请先登录教师端", code="UNAUTHORIZED", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    teacher = validate_token(token)
    if teacher is None:
        raise AppError("登录状态已失效，请重新登录", code="UNAUTHORIZED", status_code=401)
    return teacher
