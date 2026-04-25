"""Common Pydantic schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str | None = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    message: str
    data: dict | None = None
