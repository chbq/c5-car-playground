"""Explicit-port synchronous serial link for a ZDT Emm pusher motor."""

import os
import re
import time

from zdt_pusher_protocol import (
    CODE_ENABLE,
    CODE_POSITION,
    CODE_STOP,
    PusherProtocolError,
    pack_enable,
    pack_relative_position,
    pack_status_query,
    pack_stop,
    parse_ack,
    parse_motor_status,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows host tests use no file lock.
    fcntl = None


class PusherLinkError(RuntimeError):
    pass


class ZdtPusherLink:
    """Minimal Emm serial client; never auto-discovers a tty device."""

    def __init__(self, port, baudrate=115200, address=1, timeout=0.2,
                 serial_factory=None, lock_path="auto"):
        if not port or port == "auto":
            raise ValueError("pusher port must be an explicit device path")
        if baudrate <= 0:
            raise ValueError("baudrate must be positive")
        if not 0.02 <= timeout <= 2.0:
            raise ValueError("timeout must be in [0.02, 2.0]")
        self.port = str(port)
        self.baudrate = int(baudrate)
        self.address = int(address)
        self.timeout = float(timeout)
        self._serial_factory = serial_factory
        self._lock_path = lock_path
        self._serial = None
        self._lock_file = None
        self._owns_motion = False

    @property
    def is_open(self):
        return self._serial is not None and getattr(self._serial, "is_open", True)

    def _resolved_lock_path(self):
        if self._lock_path != "auto":
            return self._lock_path
        safe_port = re.sub(r"[^A-Za-z0-9_.-]", "_", self.port)
        return os.path.join("/tmp", f"c5-pusher-uart-{safe_port}.lock")

    def _acquire_lock(self):
        path = self._resolved_lock_path()
        if not path or fcntl is None:
            return
        self._lock_file = open(path, "a+", encoding="ascii")
        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock_file.close()
            self._lock_file = None
            raise PusherLinkError(
                f"pusher serial port is already owned: {self.port}") from exc

    def _release_lock(self):
        if self._lock_file is None:
            return
        if fcntl is not None:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        self._lock_file.close()
        self._lock_file = None

    def open(self):
        if self.is_open:
            return self
        self._acquire_lock()
        try:
            if self._serial_factory is None:
                try:
                    import serial
                except ImportError as exc:
                    raise PusherLinkError("pyserial is not installed") from exc
                connection = serial.Serial()
                connection.port = self.port
                connection.baudrate = self.baudrate
                connection.bytesize = 8
                connection.parity = "N"
                connection.stopbits = 1
                connection.timeout = 0.02
                connection.write_timeout = self.timeout
                connection.dtr = False
                connection.rts = False
                connection.exclusive = True
                connection.open()
                self._serial = connection
            else:
                self._serial = self._serial_factory(
                    self.port,
                    self.baudrate,
                    timeout=0.02,
                    write_timeout=self.timeout,
                )
            return self
        except Exception:
            self._serial = None
            self._release_lock()
            raise

    def close(self):
        if self._serial is None:
            self._release_lock()
            return
        if self._owns_motion:
            self.safe_stop()
        try:
            self._serial.close()
        finally:
            self._serial = None
            self._owns_motion = False
            self._release_lock()

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _write(self, frame):
        if not self.is_open:
            raise PusherLinkError("pusher serial link is not open")
        reset = getattr(self._serial, "reset_input_buffer", None)
        if reset is not None:
            reset()
        written = self._serial.write(frame)
        if written != len(frame):
            raise PusherLinkError("short pusher serial write")

    def _read_exact(self, size):
        deadline = time.monotonic() + self.timeout
        data = bytearray()
        while len(data) < size:
            chunk = self._serial.read(size - len(data))
            if chunk:
                data.extend(chunk)
                continue
            if time.monotonic() >= deadline:
                raise PusherLinkError(
                    f"pusher response timeout ({len(data)}/{size} bytes)")
        return bytes(data)

    def _ack_transaction(self, frame, code):
        self._write(frame)
        try:
            parse_ack(self._read_exact(4), code, self.address)
        except PusherProtocolError as exc:
            raise PusherLinkError(str(exc)) from exc

    def query_status(self):
        self._write(pack_status_query(self.address))
        try:
            return parse_motor_status(self._read_exact(4), self.address)
        except PusherProtocolError as exc:
            raise PusherLinkError(str(exc)) from exc

    def set_enabled(self, enabled):
        self._ack_transaction(
            pack_enable(enabled, self.address), CODE_ENABLE)
        self._owns_motion = bool(enabled)

    def move_relative(self, direction, speed_rpm, acceleration, pulses):
        if not self._owns_motion:
            raise PusherLinkError("pusher motor is not enabled by this link")
        self._ack_transaction(
            pack_relative_position(
                direction, speed_rpm, acceleration, pulses, self.address),
            CODE_POSITION,
        )

    def stop(self):
        self._ack_transaction(pack_stop(self.address), CODE_STOP)

    def safe_stop(self):
        try:
            self.stop()
            return True
        except Exception:
            return False

    def safe_disable(self):
        try:
            self.set_enabled(False)
            return True
        except Exception:
            return False
