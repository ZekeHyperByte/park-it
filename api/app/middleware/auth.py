"""Authentication middleware for FastAPI."""

from typing import Any

from fastapi import Request
from fastapi.security import APIKeyCookie

from api.app.services.auth import is_token_valid
from shared.logging import get_logger

logger = get_logger("auth_middleware")

# Cookie security scheme for docs
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)


async def get_current_user(request: Request) -> dict[str, Any] | None:
    """Extract and validate JWT from httpOnly cookie.

    Returns user payload dict or None if invalid/missing.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = await is_token_valid(token)
    if payload is None:
        return None

    return payload


async def require_auth(request: Request) -> dict[str, Any]:
    """Dependency that requires authentication.

    Raises 401 if user is not authenticated.
    """
    from fastapi import HTTPException, status

    user = await get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_role(request: Request, allowed_roles: set[str]) -> dict[str, Any]:
    """Dependency that requires specific role(s).

    Raises 403 if user role is not allowed.
    """
    from fastapi import HTTPException, status

    user = await require_auth(request)
    role = user.get("role", "operator")

    if role not in allowed_roles:
        logger.warning(
            "access_denied_wrong_role",
            user_id=user.get("sub"),
            role=role,
            required=allowed_roles,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user


# Convenience dependencies
async def require_admin(request: Request) -> dict[str, Any]:
    """Require admin role."""
    return await require_role(request, {"admin"})


async def require_operator(request: Request) -> dict[str, Any]:
    """Require operator or admin role."""
    return await require_role(request, {"admin", "operator", "supervisor"})
