"""Audit logging service.

Provides helper functions for creating audit log entries.
Designed to be called from routes and services without blocking the main flow.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models.audit_log import AuditLog
from shared.logging import get_logger

logger = get_logger("audit")


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    username: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog | None:
    """Create an audit log entry.

    Args:
        db: Database session
        action: Action type (e.g. 'CASH_PAYMENT', 'SETTING_UPDATE')
        user_id: ID of user who performed the action
        username: Username for convenience
        entity_type: Type of entity affected (e.g. 'ParkingTransaction')
        entity_id: ID of affected entity
        details: Additional structured data
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        Created AuditLog or None if creation failed
    """
    try:
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)

        logger.info(
            "audit_log_created",
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return log

    except Exception as e:
        # Audit logging should never fail the main operation
        logger.error("audit_log_failed", action=action, error=str(e))
        return None


# Convenience helpers for common actions


async def log_payment(
    db: AsyncSession,
    *,
    method: str,
    transaction_id: int,
    fee: int,
    user_id: int | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    **extra: Any,
) -> AuditLog | None:
    """Log a payment action."""
    return await log_action(
        db,
        action=f"{method}_PAYMENT",
        user_id=user_id,
        username=username,
        entity_type="ParkingTransaction",
        entity_id=str(transaction_id),
        details={"fee": fee, **extra},
        ip_address=ip_address,
    )


async def log_gate_operation(
    db: AsyncSession,
    *,
    operation: str,
    gate_id: str,
    user_id: int | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    **extra: Any,
) -> AuditLog | None:
    """Log a gate operation (open, reset, manual override)."""
    return await log_action(
        db,
        action=operation,
        user_id=user_id,
        username=username,
        entity_type="Gate",
        entity_id=gate_id,
        details=extra,
        ip_address=ip_address,
    )


async def log_setting_change(
    db: AsyncSession,
    *,
    setting_key: str,
    old_value: Any,
    new_value: Any,
    user_id: int | None = None,
    username: str | None = None,
    ip_address: str | None = None,
) -> AuditLog | None:
    """Log a settings change."""
    return await log_action(
        db,
        action="SETTING_UPDATE",
        user_id=user_id,
        username=username,
        entity_type="Setting",
        entity_id=setting_key,
        details={"old_value": old_value, "new_value": new_value},
        ip_address=ip_address,
    )


async def log_user_management(
    db: AsyncSession,
    *,
    operation: str,
    target_user_id: int,
    user_id: int | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    **extra: Any,
) -> AuditLog | None:
    """Log user management action (create, update, delete)."""
    return await log_action(
        db,
        action=f"USER_{operation}",
        user_id=user_id,
        username=username,
        entity_type="User",
        entity_id=str(target_user_id),
        details=extra,
        ip_address=ip_address,
    )
