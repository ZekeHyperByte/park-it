"""Shared shift utilities."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models.shift import Shift


async def get_current_shift(db: AsyncSession) -> Shift | None:
    """Determine the current active shift based on current time.

    Handles overnight shifts (e.g., 22:00 - 06:00).

    Args:
        db: Database session

    Returns:
        Current Shift or None if no active shifts
    """
    now = datetime.now(timezone.utc).time()

    result = await db.execute(
        select(Shift)
        .where(Shift.is_active == True)  # noqa: E712
        .order_by(Shift.start_time)
    )
    shifts = result.scalars().all()

    for shift in shifts:
        start = shift.start_time
        end = shift.end_time

        if start <= end:
            if start <= now <= end:
                return shift
        else:
            if now >= start or now <= end:
                return shift

    return shifts[0] if shifts else None
