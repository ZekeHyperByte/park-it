"""Gate Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field

class PeripheralConfig(BaseModel):
    """Base peripheral configuration."""

    enabled: bool = False


class RfidConfig(PeripheralConfig):
    """RFID reader configuration."""

    wiegand_channel: str = "W"  # W or X


class PrinterConfig(PeripheralConfig):
    """Printer configuration reference."""

    printer_id: int | None = None
    mode: str = "CONTROLLER_PASSTHROUGH"


class AudioConfig(PeripheralConfig):
    """Audio speaker configuration via Compass controller."""

    welcome_track: int = 1
    ticket_track: int = 2
    timeout_track: int = 8
    error_track: int = 11


class EmoneyConfig(PeripheralConfig):
    """E-money configuration for gate-in."""

    minimum_balance: int = 10000


class CameraConfig(PeripheralConfig):
    """Camera configuration reference."""

    camera_id: int | None = None


class OmnikeyReaderConfig(PeripheralConfig):
    """Omnikey 5427 CK HID keyboard reader at booth."""

    device_path: str | None = None
    device_name_match: str = "omnikey"


class HardwareConfig(BaseModel):
    """Complete hardware configuration for a gate."""

    gate_close_duration_ms: int = 5000
    has_close_sensor: bool = False
    relay_mode: str = "SINGLE"
    gate_open_timeout_s: int | None = 10
    sensor_stuck_s: int | None = 30

    # Serial relay barrier commands (ASCII or hex string)
    open_command: str = ""
    close_command: str = ""
    close_delay_seconds: float = 3.0

    # Lane configuration (for exit POS gates)
    lane_type: str = Field(default="MIXED", pattern="^(SINGLE|MIXED)$")
    default_vehicle_type_id: int | None = None

    # Peripherals (all optional, enabled=false by default)
    rfid: RfidConfig = Field(default_factory=RfidConfig)
    ticket_printer: PrinterConfig = Field(default_factory=PrinterConfig)
    emoney: EmoneyConfig = Field(default_factory=EmoneyConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    led: PeripheralConfig = Field(default_factory=PeripheralConfig)
    omnikey_reader: OmnikeyReaderConfig = Field(default_factory=OmnikeyReaderConfig)
    receipt_printer: PrinterConfig = Field(default_factory=PrinterConfig)


class GateBase(BaseModel):
    """Base gate fields."""

    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    direction: str = Field(..., pattern="^(IN|OUT)$")
    area_parkir_id: int | None = None
    pos_id: int | None = None
    protocol: str = Field(default="compass", pattern="^(compass|enet|serial)$")
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    controller_device: str | None = Field(None, max_length=100)
    controller_baudrate: int | None = None
    has_close_sensor: bool = False
    gate_close_duration_ms: int = Field(default=5000, ge=0)
    relay_mode: str = Field(default="SINGLE", pattern="^(SINGLE|DUAL|TRIPLE)$")
    hardware_config: HardwareConfig = Field(default_factory=HardwareConfig)
    is_active: bool = True


class GateCreate(GateBase):
    """Create gate request."""

    pass


class GateUpdate(BaseModel):
    """Update gate request (all fields optional)."""

    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=20)
    pos_id: int | None = None
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    controller_device: str | None = Field(None, max_length=100)
    controller_baudrate: int | None = None
    has_close_sensor: bool | None = None
    gate_close_duration_ms: int | None = Field(None, ge=0)
    relay_mode: str | None = Field(None, pattern="^(SINGLE|DUAL|TRIPLE)$")
    hardware_config: HardwareConfig | None = None
    is_active: bool | None = None


class GateLaneConfigUpdate(BaseModel):
    """Update only lane configuration (safe merge into hardware_config)."""

    lane_type: str = Field(..., pattern="^(SINGLE|MIXED)$")
    default_vehicle_type_id: int | None = None


class GateResponse(GateBase):
    """Gate response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_online: bool
    last_heartbeat: str | None = None
