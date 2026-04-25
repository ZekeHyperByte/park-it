"""Tests for tariff calculation engine."""

from datetime import datetime, timedelta

import pytest

from api.app.services.tariff import (
    DEFAULT_TARIFF_CONFIG,
    TariffConfig,
    VehicleTypeRate,
    calculate_tariff,
)


class TestCalculateTariff:
    """Test tariff calculation scenarios."""

    def test_grace_period(self):
        """No charge within grace period."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 10, 10, 0)  # 10 minutes

        fee = calculate_tariff(entry, exit_, "MOBIL", DEFAULT_TARIFF_CONFIG)
        assert fee == 0

    def test_one_hour(self):
        """Charge for one hour."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 11, 0, 0)

        fee = calculate_tariff(entry, exit_, "MOBIL", DEFAULT_TARIFF_CONFIG)
        assert fee == 5000

    def test_partial_hour_rounds_up(self):
        """Partial hour rounds up."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 11, 30, 0)  # 1.5 hours

        fee = calculate_tariff(entry, exit_, "MOBIL", DEFAULT_TARIFF_CONFIG)
        assert fee == 10000  # 2 hours * 5000

    def test_daily_cap(self):
        """Daily cap limits charge."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 23, 0, 0)  # 13 hours

        fee = calculate_tariff(entry, exit_, "MOBIL", DEFAULT_TARIFF_CONFIG)
        assert fee == 50000  # Daily cap, not 65000

    def test_motor_rate(self):
        """Motor rate is lower."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 12, 0, 0)  # 2 hours

        fee = calculate_tariff(entry, exit_, "MOTOR", DEFAULT_TARIFF_CONFIG)
        assert fee == 4000  # 2 * 2000

    def test_bus_rate(self):
        """Bus rate is higher."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 12, 0, 0)  # 2 hours

        fee = calculate_tariff(entry, exit_, "BUS", DEFAULT_TARIFF_CONFIG)
        assert fee == 20000  # 2 * 10000

    def test_exit_before_entry_raises(self):
        """Exit before entry raises ValueError."""
        entry = datetime(2026, 4, 25, 12, 0, 0)
        exit_ = datetime(2026, 4, 25, 10, 0, 0)

        with pytest.raises(ValueError):
            calculate_tariff(entry, exit_, "MOBIL", DEFAULT_TARIFF_CONFIG)

    def test_unknown_vehicle_type(self):
        """Unknown vehicle type raises ValueError."""
        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 11, 0, 0)

        with pytest.raises(ValueError):
            calculate_tariff(entry, exit_, "TRUCK", DEFAULT_TARIFF_CONFIG)

    def test_custom_config(self):
        """Custom configuration works."""
        config = TariffConfig(
            vehicle_types={
                "TRUCK": VehicleTypeRate(hourly_rate=15000, daily_cap=150000),
            },
            grace_period_minutes=30,
        )

        entry = datetime(2026, 4, 25, 10, 0, 0)
        exit_ = datetime(2026, 4, 25, 11, 0, 0)

        fee = calculate_tariff(entry, exit_, "TRUCK", config)
        assert fee == 15000
