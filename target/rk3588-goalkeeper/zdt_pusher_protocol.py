"""ZDT Emm free-protocol frames used by the backup pusher controller."""

from dataclasses import dataclass


CHECK_BYTE = 0x6B
CODE_STATUS = 0x3A
CODE_ENABLE = 0xF3
CODE_POSITION = 0xFD
CODE_STOP = 0xFE

RESULT_OK = 0x02
RESULT_HOME_NO_MOVE_LEFT = 0x12
RESULT_HOME_NO_MOVE_RIGHT = 0x22
RESULT_COMPLETE = 0x9F
RESULT_PARAMETER_ERROR = 0xE2
RESULT_FORMAT_ERROR = 0xEE


class PusherProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class MotorStatus:
    """Decoded response to the Emm 0x3A motor-state query."""

    raw: int
    enabled: bool
    reached: bool
    stalled: bool
    stall_protected: bool
    left_limit_high: bool
    right_limit_high: bool
    power_lost: bool


def _byte(value, name):
    value = int(value)
    if not 0 <= value <= 0xFF:
        raise PusherProtocolError(f"{name} must be in [0, 255]")
    return value


def _address(address):
    address = _byte(address, "address")
    if address == 0:
        raise PusherProtocolError("broadcast address is not allowed")
    return address


def _direction(direction):
    direction = int(direction)
    if direction not in (0, 1):
        raise PusherProtocolError("direction must be 0 (CW) or 1 (CCW)")
    return direction


def pack_status_query(address=1):
    return bytes((_address(address), CODE_STATUS, CHECK_BYTE))


def pack_enable(enabled, address=1, synchronized=False):
    return bytes((
        _address(address), CODE_ENABLE, 0xAB,
        0x01 if enabled else 0x00,
        0x01 if synchronized else 0x00,
        CHECK_BYTE,
    ))


def pack_relative_position(direction, speed_rpm, acceleration, pulses,
                           address=1, synchronized=False):
    """Build Emm 0xFD relative-to-current-position mode 2 command."""
    direction = _direction(direction)
    speed_rpm = int(speed_rpm)
    acceleration = int(acceleration)
    pulses = int(pulses)
    if not 1 <= speed_rpm <= 3000:
        raise PusherProtocolError("speed_rpm must be in [1, 3000]")
    if not 0 <= acceleration <= 255:
        raise PusherProtocolError("acceleration must be in [0, 255]")
    if not 1 <= pulses <= 0xFFFFFFFF:
        raise PusherProtocolError("pulses must be in [1, 4294967295]")
    return bytes((
        _address(address), CODE_POSITION, direction,
        (speed_rpm >> 8) & 0xFF, speed_rpm & 0xFF,
        acceleration,
        (pulses >> 24) & 0xFF, (pulses >> 16) & 0xFF,
        (pulses >> 8) & 0xFF, pulses & 0xFF,
        0x02,
        0x01 if synchronized else 0x00,
        CHECK_BYTE,
    ))


def pack_stop(address=1, synchronized=False):
    return bytes((
        _address(address), CODE_STOP, 0x98,
        0x01 if synchronized else 0x00,
        CHECK_BYTE,
    ))


def parse_ack(frame, expected_code, address=1):
    frame = bytes(frame)
    if len(frame) != 4:
        raise PusherProtocolError("acknowledgement must be 4 bytes")
    if frame[0] != _address(address):
        raise PusherProtocolError("unexpected motor address")
    if frame[1] != _byte(expected_code, "expected_code"):
        raise PusherProtocolError("unexpected acknowledgement function code")
    if frame[3] != CHECK_BYTE:
        raise PusherProtocolError("invalid acknowledgement check byte")
    if frame[2] != RESULT_OK:
        name = {
            RESULT_HOME_NO_MOVE_LEFT: "HOME_NO_MOVE_LEFT",
            RESULT_HOME_NO_MOVE_RIGHT: "HOME_NO_MOVE_RIGHT",
            RESULT_COMPLETE: "COMPLETE",
            RESULT_PARAMETER_ERROR: "PARAMETER_ERROR",
            RESULT_FORMAT_ERROR: "FORMAT_ERROR",
        }.get(frame[2], f"0x{frame[2]:02X}")
        raise PusherProtocolError(f"motor rejected command: {name}")
    return True


def parse_motor_status(frame, address=1):
    frame = bytes(frame)
    if len(frame) != 4:
        raise PusherProtocolError("motor status must be 4 bytes")
    if frame[0] != _address(address) or frame[1] != CODE_STATUS:
        raise PusherProtocolError("unexpected motor status header")
    if frame[3] != CHECK_BYTE:
        raise PusherProtocolError("invalid motor status check byte")
    value = frame[2]
    return MotorStatus(
        raw=value,
        enabled=bool(value & 0x01),
        reached=bool(value & 0x02),
        stalled=bool(value & 0x04),
        stall_protected=bool(value & 0x08),
        left_limit_high=bool(value & 0x10),
        right_limit_high=bool(value & 0x20),
        power_lost=bool(value & 0x80),
    )
