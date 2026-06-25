"""Async database configuration.

NOTE: This module is for api/ ONLY. Daemons must never import this.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.app.models.base import Base
from shared.config import get_settings

settings = get_settings()

# Async engine.
# `statement_cache_size=0` + `prepared_statement_cache_size=0` keep the engine
# safe behind pgbouncer in transaction pooling mode (asyncpg requirement).
# `pool_recycle=1800` drops connections older than 30 min to avoid stale
# sockets after long idle (e.g. firewall NAT drop, postgres restart).
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Re-export Base for Alembic and other consumers
__all__ = ["Base", "engine", "AsyncSessionLocal", "get_db"]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependency injection.

    Automatically commits on success or rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
