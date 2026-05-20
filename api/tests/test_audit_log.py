"""Tests for audit logging service."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.services.audit import (
    log_action,
    log_gate_operation,
    log_payment,
    log_setting_change,
    log_user_management,
)


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


class TestLogPayment:
    @pytest.mark.asyncio
    async def test_log_cash_payment(self, db_session: AsyncSession):
        """Should log a cash payment action."""
        log = await log_payment(
            db_session,
            method="CASH",
            transaction_id=42,
            fee=5000,
            user_id=1,
            username="operator",
            ip_address="10.0.0.1",
            paid_amount=10000,
            change=5000,
        )

        assert log is not None
        assert log.action == "CASH_PAYMENT"
        assert log.entity_type == "ParkingTransaction"
        assert log.entity_id == "42"
        assert log.details["fee"] == 5000
        assert log.details["paid_amount"] == 10000


class TestLogGateOperation:
    @pytest.mark.asyncio
    async def test_log_manual_open(self, db_session: AsyncSession):
        """Should log a manual gate open."""
        log = await log_gate_operation(
            db_session,
            operation="MANUAL_GATE_OPEN",
            gate_id="gate-out-1",
            user_id=1,
            reason="operator_override",
        )

        assert log is not None
        assert log.action == "MANUAL_GATE_OPEN"
        assert log.entity_type == "Gate"
        assert log.entity_id == "gate-out-1"
        assert log.details["reason"] == "operator_override"


class TestLogSettingChange:
    @pytest.mark.asyncio
    async def test_log_setting_update(self, db_session: AsyncSession):
        """Should log a settings change."""
        log = await log_setting_change(
            db_session,
            setting_key="location_name",
            old_value="Old Location",
            new_value="New Location",
            user_id=1,
        )

        assert log is not None
        assert log.action == "SETTING_UPDATE"
        assert log.entity_type == "Setting"
        assert log.entity_id == "location_name"
        assert log.details["old_value"] == "Old Location"
        assert log.details["new_value"] == "New Location"


class TestLogUserManagement:
    @pytest.mark.asyncio
    async def test_log_user_create(self, db_session: AsyncSession):
        """Should log user creation."""
        log = await log_user_management(
            db_session,
            operation="CREATE",
            target_user_id=99,
            user_id=1,
            username="admin",
            role="operator",
        )

        assert log is not None
        assert log.action == "USER_CREATE"
        assert log.entity_type == "User"
        assert log.entity_id == "99"
        assert log.details["role"] == "operator"
