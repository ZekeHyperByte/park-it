"""Gate Pydantic schemas."""

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Gate In
# =============================================================================

class GateInBase(BaseModel):
    """Base gate-in fields."""

    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    area_parkir_id: int | None = None
    protocol: str = Field(default="compass", pattern="^(compass|enet)$")
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    gate_mode: str = Field(default="CASH", pattern="^(CASH|RFID|EMONEY)$")
    emoney_minimum_balance: int = Field(default=10000, ge=0)
    print_decision_timeout_seconds: int = Field(default=10, ge=1)
    has_close_sensor: bool = False
    gate_close_duration_ms: int = Field(default=5000, ge=0)
    relay_mode: str = Field(default="SINGLE", pattern="^(SINGLE|DUAL)$")
    open_command: str | None = Field(None, max_length=50)
    close_command: str | None = Field(None, max_length=50)
    pulse_duration_ms: int | None = None
    gate_open_timeout_s: int | None = None
    sensor_stuck_s: int | None = None
    audio_module: str | None = Field(None, max_length=50)
    led_display: str | None = Field(None, max_length=50)
    printer_name: str | None = Field(None, max_length=100)
    printer_type: str | None = Field(None, max_length=20)
    camera_url: str | None = Field(None, max_length=500)
    camera_name: str | None = Field(None, max_length=100)
    is_active: bool = True


class GateInCreate(GateInBase):
    """Create gate-in request."""

    pass


class GateInUpdate(BaseModel):
    """Update gate-in request."""

    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=20)
    area_parkir_id: int | None = None
    protocol: str | None = Field(None, pattern="^(compass|enet)$")
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    gate_mode: str | None = Field(None, pattern="^(CASH|RFID|EMONEY)$")
    emoney_minimum_balance: int | None = Field(None, ge=0)
    print_decision_timeout_seconds: int | None = Field(None, ge=1)
    has_close_sensor: bool | None = None
    gate_close_duration_ms: int | None = Field(None, ge=0)
    relay_mode: str | None = Field(None, pattern="^(SINGLE|DUAL)$")
    open_command: str | None = Field(None, max_length=50)
    close_command: str | None = Field(None, max_length=50)
    pulse_duration_ms: int | None = None
    gate_open_timeout_s: int | None = None
    sensor_stuck_s: int | None = None
    audio_module: str | None = Field(None, max_length=50)
    led_display: str | None = Field(None, max_length=50)
    printer_name: str | None = Field(None, max_length=100)
    printer_type: str | None = Field(None, max_length=20)
    camera_url: str | None = Field(None, max_length=500)
    camera_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class GateInResponse(GateInBase):
    """Gate-in response."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# =============================================================================
# Gate Out
# =============================================================================

class GateOutBase(BaseModel):
    """Base gate-out fields."""

    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    area_parkir_id: int | None = None
    protocol: str = Field(default="compass", pattern="^(compass|enet)$")
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    emoney_reader_id: int | None = None
    payment_timeout_seconds: int = Field(default=120, ge=10)
    has_close_sensor: bool = False
    gate_close_duration_ms: int = Field(default=5000, ge=0)
    relay_mode: str = Field(default="SINGLE", pattern="^(SINGLE|DUAL)$")
    open_command: str | None = Field(None, max_length=50)
    close_command: str | None = Field(None, max_length=50)
    pulse_duration_ms: int | None = None
    gate_open_timeout_s: int | None = None
    sensor_stuck_s: int | None = None
    audio_module: str | None = Field(None, max_length=50)
    led_display: str | None = Field(None, max_length=50)
    printer_name: str | None = Field(None, max_length=100)
    printer_type: str | None = Field(None, max_length=20)
    camera_url: str | None = Field(None, max_length=500)
    camera_name: str | None = Field(None, max_length=100)
    is_active: bool = True


class GateOutCreate(GateOutBase):
    """Create gate-out request."""

    pass


class GateOutUpdate(BaseModel):
    """Update gate-out request."""

    name: str | None = Field(None, max_length=100)
    code: str | None = Field(None, max_length=20)
    area_parkir_id: int | None = None
    protocol: str | None = Field(None, pattern="^(compass|enet)$")
    controller_host: str | None = Field(None, max_length=100)
    controller_port: int | None = None
    emoney_reader_id: int | None = None
    payment_timeout_seconds: int | None = Field(None, ge=10)
    has_close_sensor: bool | None = None
    gate_close_duration_ms: int | None = Field(None, ge=0)
    relay_mode: str | None = Field(None, pattern="^(SINGLE|DUAL)$")
    open_command: str | None = Field(None, max_length=50)
    close_command: str | None = Field(None, max_length=50)
    pulse_duration_ms: int | None = None
    gate_open_timeout_s: int | None = None
    sensor_stuck_s: int | None = None
    audio_module: str | None = Field(None, max_length=50)
    led_display: str | None = Field(None, max_length=50)
    printer_name: str | None = Field(None, max_length=100)
    printer_type: str | None = Field(None, max_length=20)
    camera_url: str | None = Field(None, max_length=500)
    camera_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None


class GateOutResponse(GateOutBase):
    """Gate-out response."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# =============================================================================
# Unified Gate (New — replaces GateIn/GateOut)
# =============================================================================

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


class UhfReaderConfig(PeripheralConfig):
    """UHF RFID reader for gate-out."""

    host: str | None = None
    port: int | None = None


class HardwareConfig(BaseModel):
    """Complete hardware configuration for a gate."""

    gate_close_duration_ms: int = 5000
    has_close_sensor: bool = False
    relay_mode: str = "SINGLE"
    gate_open_timeout_s: int | None = 10
    sensor_stuck_s: int | None = 30

    # Peripherals (all optional, enabled=false by default)
    rfid: RfidConfig = Field(default_factory=RfidConfig)
    ticket_printer: PrinterConfig = Field(default_factory=PrinterConfig)
    emoney: EmoneyConfig = Field(default_factory=EmoneyConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    led: PeripheralConfig = Field(default_factory=PeripheralConfig)
    uhf_reader: UhfReaderConfig = Field(default_factory=UhfReaderConfig)
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
    relay_mode: str = Field(default="SINGLE", pattern="^(SINGLE|DUAL)$")
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
    relay_mode: str | None = Field(None, pattern="^(SINGLE|DUAL)$")
    hardware_config: HardwareConfig | None = None
    is_active: bool | None = None


class GateResponse(GateBase):
    """Gate response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_online: bool
    last_heartbeat: str | None = None
