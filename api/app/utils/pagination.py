"""Pagination utilities for list endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PaginationParams(BaseModel):
    """FastAPI dependency for pagination query params."""

    skip: int = 0
    limit: int = 100
    q: str | None = None


class PaginatedList(BaseModel):
    """Generic paginated response."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[Any]
    total: int
    skip: int
    limit: int


async def paginated_list(
    session: AsyncSession,
    stmt,
    count_stmt=None,
    skip: int = 0,
    limit: int = 100,
) -> PaginatedList:
    """Execute a paginated query.

    Args:
        session: Async SQLAlchemy session.
        stmt: Select statement for items.
        count_stmt: Optional count statement (defaults to COUNT(*)).
        skip: Number of items to skip.
        limit: Maximum items to return.

    Returns:
        PaginatedList with items and total count.
    """
    # Total count
    if count_stmt is None:
        count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Items
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return PaginatedList(
        items=list(items),
        total=total,
        skip=skip,
        limit=limit,
    )
