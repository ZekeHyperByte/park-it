"""Tests for audit logging service."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.services.audit import log_action


class TestLogAction:
    @pytest.mark.asyncio
    async def test_create_basic_log(self, db_session: AsyncSession):
        """Should create a basic audit log entry."""
        log = await log_action(
            db_session,
            action="TEST_ACTION",
            user_id=1,
            username="admin",
            entity_type="Test",
            entity_id="123",
            details={"key": "value"},
            ip_address="192.168.1.1",
        )

        assert log is not None
        assert log.action == "TEST_ACTION"
        assert log.user_id == 1
        assert log.username == "admin"
        assert log.entity_type == "Test"
        assert log.entity_id == "123"
        assert log.details == {"key": "value"}
        assert log.ip_address == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_create_minimal_log(self, db_session: AsyncSession):
        """Should create a log with minimal fields."""
        log = await log_action(
            db_session,
            action="MINIMAL_ACTION",
        )

        assert log is not None
        assert log.action == "MINIMAL_ACTION"
        assert log.user_id is None
        assert log.details == {}

    @pytest.mark.asyncio
    async def test_none_details_becomes_empty_dict(self, db_session: AsyncSession):
        """None details should be stored as empty dict."""
        log = await log_action(
            db_session,
            action="TEST",
            details=None,
        )

        assert log is not None
        assert log.details == {}
