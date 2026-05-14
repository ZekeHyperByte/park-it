"""Setup wizard routes — token redeem, admin create, preflight, state I/O.

Authentication model:
- `/api/setup/redeem-token` is the only un-auth endpoint. It validates a
  one-time token written to disk by the installer, sets a setup-session
  cookie (`parking_setup_session`), and returns a fresh setup session row.
- Subsequent endpoints accept either a valid setup session cookie OR an
  admin JWT. This allows re-running the wizard via `/setup?force=1` after
  initial setup.
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.middleware.auth import get_current_user
from api.app.models.setup_session import SetupSession
from api.app.models.user import User
from api.app.schemas.common import SuccessResponse
from api.app.schemas.setup import (
    CreateAdminRequest,
    PreflightCheckResult,
    PreflightResponse,
    RedeemTokenRequest,
    SetupStateResponse,
    SetupStateUpdate,
)
from api.app.schemas.user import UserResponse
from api.app.services.auth import create_tokens
from api.app.services.setup import (
    constant_time_eq,
    create_session,
    delete_setup_token,
    detect_topology,
    get_session_by_token,
    has_any_admin,
    read_setup_token,
    save_session_step,
    setup_complete as setup_complete_q,
)
from api.app.utils.password import hash_password
from api.database import get_db
from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("setup_routes")

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])

SETUP_COOKIE_NAME = "parking_setup_session"


def _set_setup_cookie(response: Response, token: str) -> None:
    is_secure = get_settings().app_env == "production"
    response.set_cookie(
        key=SETUP_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_secure,
        samesite="strict",
        max_age=get_settings().setup_session_ttl_seconds,
        path="/",
    )


def _clear_setup_cookie(response: Response) -> None:
    response.delete_cookie(key=SETUP_COOKIE_NAME, path="/")


async def require_setup_or_admin(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[SetupSession | None, dict[str, Any] | None]:
    """Allow the request if either a valid setup-session cookie OR admin JWT is present."""
    cookie = request.cookies.get(SETUP_COOKIE_NAME)
    session: SetupSession | None = None
    if cookie:
        session = await get_session_by_token(db, cookie)

    user_payload = await get_current_user(request)
    is_admin = user_payload is not None and user_payload.get("role") == "admin"

    if session is None and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Setup session or admin authentication required",
        )
    return session, user_payload


@router.get("/state", response_model=SetupStateResponse)
async def get_state(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SetupStateResponse:
    """Wizard bootstrapping endpoint. Public (no auth)."""
    complete = await setup_complete_q(db)
    has_admin = await has_any_admin(db)
    topology = await detect_topology()

    cookie = request.cookies.get(SETUP_COOKIE_NAME)
    session: SetupSession | None = None
    if cookie:
        session = await get_session_by_token(db, cookie)

    return SetupStateResponse(
        setup_complete=complete,
        current_step=session.current_step if session else None,
        topology=topology,
        has_admin=has_admin,
        has_session=session is not None,
    )


@router.post("/redeem-token", response_model=SuccessResponse)
async def redeem_token(
    body: RedeemTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Validate installer-written token and issue setup session cookie."""
    disk_token = read_setup_token()
    if not disk_token:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Setup token not present — installer must regenerate one.",
        )
    if not constant_time_eq(disk_token, body.token):
        logger.warning("setup_token_mismatch")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid setup token",
        )

    delete_setup_token()
    session = await create_session(db)
    _set_setup_cookie(response, session.session_token)
    logger.info("setup_session_created", session_id=session.id)
    return SuccessResponse(
        message="Setup session active",
        data={"current_step": session.current_step},
    )


@router.post("/logout", response_model=SuccessResponse)
async def setup_logout(response: Response) -> SuccessResponse:
    """Clear setup session cookie (does not delete server row)."""
    _clear_setup_cookie(response)
    return SuccessResponse(message="Setup session cleared")


@router.post("/create-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: CreateAdminRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create first admin during wizard. Refused if any admin already exists.

    On success, issues real auth cookies so subsequent CRUD endpoints work.
    """
    cookie = request.cookies.get(SETUP_COOKIE_NAME)
    session = await get_session_by_token(db, cookie) if cookie else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Setup session required",
        )

    if await has_any_admin(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin already exists. Use the standard login flow.",
        )

    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    tokens = await create_tokens(user)
    is_secure = get_settings().app_env == "production"
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=1800,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=604800,
    )

    logger.info("setup_admin_created", user_id=user.id)
    return UserResponse.model_validate(user)


@router.get("/preflight", response_model=PreflightResponse)
async def preflight(
    auth=Depends(require_setup_or_admin),
) -> PreflightResponse:
    """Run the existing scripts/preflight_check.py logic and return JSON."""
    sys.path.insert(0, str(get_settings().parking_install_root))
    try:
        from scripts import preflight_check  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - scripts may not import cleanly outside install
        try:
            import importlib.util
            from pathlib import Path

            script = Path(get_settings().parking_install_root) / "scripts" / "preflight_check.py"
            spec = importlib.util.spec_from_file_location("preflight_check", script)
            if spec is None or spec.loader is None:
                raise FileNotFoundError(str(script))
            preflight_check = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(preflight_check)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            logger.warning("preflight_unavailable", error=str(exc))
            return PreflightResponse(checks=[], passed=0, warnings=0, failed=0)

    try:
        runner = await preflight_check.run_all_checks()  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        logger.warning("preflight_runner_failed", error=str(exc))
        return PreflightResponse(checks=[], passed=0, warnings=0, failed=0)

    summary = runner.summary()
    return PreflightResponse(
        checks=[PreflightCheckResult(**c.to_dict()) for c in runner.checks],
        passed=summary.get("passed", 0),
        warnings=summary.get("warnings", 0),
        failed=summary.get("failed", 0),
    )


@router.post("/state", response_model=SuccessResponse)
async def save_state(
    body: SetupStateUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """Persist a wizard step's data for resume across reloads."""
    cookie = request.cookies.get(SETUP_COOKIE_NAME)
    session = await get_session_by_token(db, cookie) if cookie else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Setup session required",
        )
    await save_session_step(db, session, step=body.step, data=body.data)
    return SuccessResponse(message="Step saved", data={"step": body.step})


@router.get("/session", response_model=dict)
async def read_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current session state for resume."""
    cookie = request.cookies.get(SETUP_COOKIE_NAME)
    session = await get_session_by_token(db, cookie) if cookie else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active setup session",
        )
    return {"current_step": session.current_step, "data": session.data}
