"""Authentication routes."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import get_current_user
from api.app.schemas.auth import LoginRequest
from api.app.schemas.common import ErrorResponse, SuccessResponse
from api.app.schemas.user import UserResponse
from api.app.services.auth import authenticate_user, create_tokens, refresh_tokens, revoke_token
from api.app.services.user import get_user_by_id
from api.database import get_db
from shared.logging import get_logger

logger = get_logger("auth_routes")

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly auth cookies."""
    from shared.config import get_settings

    is_secure = get_settings().app_env == "production"
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=1800,  # 30 minutes
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=604800,  # 7 days
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies."""
    response.delete_cookie(key=ACCESS_COOKIE_NAME)
    response.delete_cookie(key=REFRESH_COOKIE_NAME)


@router.post(
    "/login",
    response_model=SuccessResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Authenticate user and set httpOnly JWT cookies."""
    user = await authenticate_user(db, login_data.username, login_data.password)
    if user is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return SuccessResponse(message="Invalid username or password")

    tokens = await create_tokens(user)
    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

    logger.info("login_success", username=user.username, user_id=user.id)
    return SuccessResponse(
        message="Login successful",
        data={"user": {"id": user.id, "username": user.username, "role": user.role}},
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(request: Request, response: Response) -> SuccessResponse:
    """Logout user and revoke tokens."""
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if access_token:
        await revoke_token(access_token)
    if refresh_token:
        await revoke_token(refresh_token)

    _clear_auth_cookies(response)
    logger.info("logout_success")
    return SuccessResponse(message="Logout successful")


@router.post("/refresh", response_model=SuccessResponse)
async def refresh(request: Request, response: Response) -> SuccessResponse:
    """Refresh access token using refresh token."""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not refresh_token:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return SuccessResponse(message="Refresh token missing")

    tokens = await refresh_tokens(refresh_token)
    if tokens is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return SuccessResponse(message="Invalid or expired refresh token")

    _set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
    return SuccessResponse(message="Token refreshed")


@router.get("/me", response_model=UserResponse)
async def me(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get current authenticated user."""
    from fastapi import HTTPException

    user_payload = await get_current_user(request)
    if user_payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        user_id = int(user_payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserResponse.model_validate(user)
