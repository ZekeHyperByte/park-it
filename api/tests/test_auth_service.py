"""Tests for authentication service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.schemas.user import UserCreate
from api.app.services.auth import authenticate_user, create_tokens
from api.app.services.user import create_user


class TestAuthenticateUser:
    """Test user authentication."""

    @pytest.mark.asyncio
    async def test_success(self, db_session: AsyncSession):
        """Authenticate with correct credentials."""
        # Create user
        user_data = UserCreate(
            username="testuser",
            password="testpass123",
            full_name="Test User",
            role="operator",
        )
        user = await create_user(db_session, user_data)

        # Authenticate
        result = await authenticate_user(db_session, "testuser", "testpass123")
        assert result is not None
        assert result.id == user.id
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_wrong_password(self, db_session: AsyncSession):
        """Authenticate with wrong password."""
        user_data = UserCreate(
            username="testuser",
            password="testpass123",
            role="operator",
        )
        await create_user(db_session, user_data)

        result = await authenticate_user(db_session, "testuser", "wrongpass")
        assert result is None

    @pytest.mark.asyncio
    async def test_user_not_found(self, db_session: AsyncSession):
        """Authenticate non-existent user."""
        result = await authenticate_user(db_session, "nonexistent", "password")
        assert result is None

    @pytest.mark.asyncio
    async def test_inactive_user(self, db_session: AsyncSession):
        """Authenticate inactive user."""
        user_data = UserCreate(
            username="inactive",
            password="testpass123",
            role="operator",
            is_active=False,
        )
        await create_user(db_session, user_data)

        result = await authenticate_user(db_session, "inactive", "testpass123")
        assert result is None


class TestCreateTokens:
    """Test token creation."""

    @pytest.mark.asyncio
    async def test_creates_both_tokens(self, db_session: AsyncSession):
        """Create access and refresh tokens."""
        user_data = UserCreate(
            username="tokenuser",
            password="testpass123",
            role="admin",
        )
        user = await create_user(db_session, user_data)

        tokens = await create_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["access_token"] != tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_token_contains_user_data(self, db_session: AsyncSession):
        """Tokens contain user claims."""
        user_data = UserCreate(
            username="claimuser",
            password="testpass123",
            role="operator",
        )
        user = await create_user(db_session, user_data)

        tokens = await create_tokens(user)

        from api.app.utils.jwt import decode_token

        access_payload = decode_token(tokens["access_token"])
        assert access_payload["sub"] == str(user.id)
        assert access_payload["username"] == "claimuser"
        assert access_payload["role"] == "operator"
