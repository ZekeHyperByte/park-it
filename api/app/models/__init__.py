"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can discover them.
"""

from api.app.models.abandoned_vehicle_log import AbandonedVehicleLog
from api.app.models.area_parkir import AreaParkir
from api.app.models.audit_log import AuditLog
from api.app.models.camera import Camera
from api.app.models.emoney_reader import EmoneyReader
from api.app.models.emoney_settlement import EmoneySettlement
from api.app.models.emoney_transaction import EmoneyTransaction
from api.app.models.gate import Gate
from api.app.models.health_check import HealthCheck
from api.app.models.manual_open_log import ManualOpenLog
from api.app.models.member import Member
from api.app.models.member_group import MemberGroup
from api.app.models.member_renewal import MemberRenewal
from api.app.models.operator_alert import OperatorAlert
from api.app.models.parking_transaction import ParkingTransaction
from api.app.models.pos import Pos
from api.app.models.printer import Printer
from api.app.models.setting import Setting
from api.app.models.shift import Shift
from api.app.models.site_config import SiteConfig
from api.app.models.shift_emoney_snapshot import ShiftEmoneySnapshot
from api.app.models.snapshot import Snapshot
from api.app.models.user import User
from api.app.models.vehicle_type import VehicleType

__all__ = [
    "AbandonedVehicleLog",
    "AreaParkir",
    "AuditLog",
    "Camera",
    "EmoneyReader",
    "EmoneySettlement",
    "EmoneyTransaction",
    "Gate",
    "HealthCheck",
    "ManualOpenLog",
    "Member",
    "MemberGroup",
    "MemberRenewal",
    "OperatorAlert",
    "ParkingTransaction",
    "Pos",
    "Printer",
    "Setting",
    "Shift",
    "SiteConfig",
    "ShiftEmoneySnapshot",
    "Snapshot",
    "User",
    "VehicleType",
]
