"""Common Pydantic schemas."""

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Standard success response."""

    message: str
    data: dict | None = None
