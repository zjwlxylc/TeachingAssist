from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    code: str = "OK"
    message: str = "success"
    data: T | None = None


def ok(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    return ApiResponse(data=data, message=message)
