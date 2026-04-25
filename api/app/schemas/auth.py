"""Authentication Pydantic schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response (only for docs — actual tokens are in httpOnly cookies)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str
