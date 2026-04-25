"""Tariff calculation engine.

This module provides configurable tariff calculation. Rates are not hardcoded;
they are passed as parameters, allowing the system to be configured at setup time
or changed dynamically via the admin settings.

Example configuration (stored in Setting model or config file):
    {
        "vehicle_types": {
            "MOTOR": {"hourly_rate": 2000, "daily_cap": 15000},
            "MOBIL": {"hourly_rate": 5000, "daily_cap": 50000},
            "BUS":   {"hourly_rate": 10000, "daily_cap": 100000}
        },
        "grace_period_minutes": 15,
        "overnight_additional": 0,
        "overnight_start_hour": 24
    }
"""

from dataclasses import dataclass
from datetime import datetime
from math import ceil


@dataclass
class VehicleTypeRate:
    """Rate configuration for a vehicle type."""

    hourly_rate: int  # Rupiah per hour (or partial hour)
    daily_cap: int  # Maximum charge per day


@dataclass
class TariffConfig:
    """Complete tariff configuration."""

    vehicle_types: dict[str, VehicleTypeRate]
    grace_period_minutes: int = 15
    overnight_additional: int = 0
    overnight_start_hour: int = 24  # Hour at which overnight charge applies


def calculate_tariff(
    entry_time: datetime,
    exit_time: datetime,
    vehicle_type_code: str,
    config: TariffConfig,
) -> int:
    """Calculate parking fee based on entry/exit time and vehicle type.

    Args:
        entry_time: When vehicle entered
        exit_time: When vehicle exited
        vehicle_type_code: Key in config.vehicle_types (e.g. "MOTOR", "MOBIL")
        config: Tariff configuration

    Returns:
        Fee in Rupiah
    """
    if exit_time < entry_time:
        raise ValueError("exit_time must be after entry_time")

    rate = config.vehicle_types.get(vehicle_type_code)
    if rate is None:
        raise ValueError(f"Unknown vehicle type: {vehicle_type_code}")

    duration_minutes = (exit_time - entry_time).total_seconds() / 60

    # Grace period: no charge
    if duration_minutes <= config.grace_period_minutes:
        return 0

    # Calculate hours (round up partial hours)
    hours = ceil(duration_minutes / 60)

    # Base fee
    fee = hours * rate.hourly_rate

    # Overnight additional (if applicable)
    if config.overnight_additional > 0:
        entry_hour = entry_time.hour
        exit_hour = exit_time.hour
        if exit_hour >= config.overnight_start_hour or entry_hour >= config.overnight_start_hour:
            fee += config.overnight_additional

    # Daily cap
    fee = min(fee, rate.daily_cap)

    return fee


# Default configuration for development / first-time setup
DEFAULT_TARIFF_CONFIG = TariffConfig(
    vehicle_types={
        "MOTOR": VehicleTypeRate(hourly_rate=2000, daily_cap=15000),
        "MOBIL": VehicleTypeRate(hourly_rate=5000, daily_cap=50000),
        "BUS": VehicleTypeRate(hourly_rate=10000, daily_cap=100000),
    },
    grace_period_minutes=15,
    overnight_additional=0,
    overnight_start_hour=24,
)
