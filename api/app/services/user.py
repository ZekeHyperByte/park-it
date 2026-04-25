"""User service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.models.user import User
from api.app.schemas.user import UserCreate, UserUpdate
from api.app.utils.password import hash_password
from shared.logging import get_logger

logger = get_logger("user_service")


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    """Create a new user."""
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        is_active=data.is_active,
        phone=data.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("user_created", user_id=user.id, username=user.username)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """List users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_users(db: AsyncSession) -> int:
    """Count total users."""
    from sqlalchemy import func
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar() or 0


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    """Update an existing user."""
    update_data = data.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    logger.info("user_updated", user_id=user.id)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    """Delete a user."""
    await db.delete(user)
    await db.commit()
    logger.info("user_deleted", user_id=user.id)
