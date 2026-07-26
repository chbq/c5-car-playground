"""Fixed 11-byte C5 HOST motion protocol."""

from dataclasses import dataclass
from enum import IntEnum
import struct

FRAME_SIZE = 11
SYNC = b"\xA5\x5A"
AXIS_LIMIT = 1000
STATUS_TYPE = 0x80


class CommandType(IntEnum):
    ARM = 0x01
    TWIST = 0x02
    STOP = 0x03
    QUERY = 0x04


class Result(IntEnum):
    OK = 0
    BAD_CRC = 1
    BAD_TYPE = 2
    BAD_PAYLOAD = 3
    MODE_DENIED = 4
    NOT_ARMED = 5
    MOTION_FAULT = 6
    RX_OVERFLOW = 7
    UART_ERROR = 8


class ControlMode(IntEnum):
    HOST = 0
    PS2 = 1


class HostState(IntEnum):
    DISARMED = 0
    ARMED = 1


class MotionState(IntEnum):
    UNINITIALIZED = 0
    STOPPED = 1
    MOVING = 2
    FAULT = 3


@dataclass(frozen=True)
class Status:
    sequence: int
    result: Result
    mode: ControlMode
    host_state: HostState
    motion_state: MotionState
    error_count: int


def crc8(data: bytes) -> int:
    """Return CRC-8/ATM: poly=0x07, init=0, refin=false, xorout=0."""
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def pack_command(command: CommandType, sequence: int,
                 vx: int = 0, vy: int = 0, wz: int = 0) -> bytes:
    command = CommandType(command)
    if not 0 <= sequence <= 0xFF:
        raise ValueError("sequence must be in [0, 255]")
    axes = (int(vx), int(vy), int(wz))
    if command == CommandType.TWIST:
        if any(value < -AXIS_LIMIT or value > AXIS_LIMIT for value in axes):
            raise ValueError("vx, vy and wz must be in [-1000, 1000]")
    elif any(axes):
        raise ValueError("ARM, STOP and QUERY require zero axes")
    body = struct.pack("<BBhhh", int(command), sequence, *axes)
    return SYNC + body + bytes((crc8(body),))


def unpack_status(frame: bytes) -> Status:
    if len(frame) != FRAME_SIZE:
        raise ValueError("status frame must contain 11 bytes")
    if frame[:2] != SYNC:
        raise ValueError("invalid status sync")
    if crc8(frame[2:10]) != frame[10]:
        raise ValueError("invalid status CRC8")
    frame_type, sequence, result, mode, host, motion, errors = struct.unpack(
        "<BBBBBBH", frame[2:10]
    )
    if frame_type != STATUS_TYPE:
        raise ValueError("unexpected status frame type")
    return Status(
        sequence=sequence,
        result=Result(result),
        mode=ControlMode(mode),
        host_state=HostState(host),
        motion_state=MotionState(motion),
        error_count=errors,
    )


def pack_status(status: Status) -> bytes:
    """Pack a status frame for tests and link simulators."""
    body = struct.pack(
        "<BBBBBBH",
        STATUS_TYPE,
        int(status.sequence),
        int(status.result),
        int(status.mode),
        int(status.host_state),
        int(status.motion_state),
        int(status.error_count),
    )
    return SYNC + body + bytes((crc8(body),))


class FrameParser:
    """Incremental fixed-frame parser with sync recovery."""

    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes):
        frames = []
        for value in data:
            if not self._buffer:
                if value == SYNC[0]:
                    self._buffer.append(value)
                continue
            if len(self._buffer) == 1:
                if value == SYNC[1]:
                    self._buffer.append(value)
                elif value != SYNC[0]:
                    self._buffer.clear()
                continue
            self._buffer.append(value)
            if len(self._buffer) == FRAME_SIZE:
                frames.append(bytes(self._buffer))
                self._buffer.clear()
        return frames
