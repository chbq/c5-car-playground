"""Thread-safe serial client for the C5 HOST motion link."""

from collections import OrderedDict
import os
import re
import threading
import time

from motion_protocol import (
    CommandType,
    ControlMode,
    FrameParser,
    HostState,
    Result,
    pack_command,
    unpack_status,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows host tests use no file lock.
    fcntl = None


class MotionLinkError(RuntimeError):
    pass


class MotionLink:
    """Synchronous command API backed by a serial reader thread."""

    def __init__(self, port="/dev/ttyS7", baudrate=115200,
                 ack_timeout=0.2, status_timeout=0.2,
                 status_callback=None, serial_factory=None,
                 lock_path="auto"):
        self.port = port
        self.baudrate = baudrate
        self.ack_timeout = ack_timeout
        self.status_timeout = status_timeout
        self.status_callback = status_callback
        self._serial_factory = serial_factory
        self._lock_path = lock_path
        self._serial = None
        self._lock_file = None
        self._parser = FrameParser()
        self._condition = threading.Condition()
        self._write_lock = threading.Lock()
        self._statuses = OrderedDict()
        self._thread = None
        self._running = False
        self._sequence = 0
        self._armed = False
        self._faulted = False
        self._last_status = None
        self._last_status_time = 0.0
        self._reader_error = None

    @property
    def is_open(self):
        return self._serial is not None and getattr(self._serial, "is_open", True)

    @property
    def is_armed(self):
        with self._condition:
            return self._armed

    @property
    def last_status(self):
        with self._condition:
            return self._last_status

    def _resolved_lock_path(self):
        if self._lock_path != "auto":
            return self._lock_path
        safe_port = re.sub(r"[^A-Za-z0-9_.-]", "_", self.port)
        return os.path.join("/tmp", f"c5-host-uart-{safe_port}.lock")

    def _acquire_port_lock(self):
        path = self._resolved_lock_path()
        if not path or fcntl is None:
            return
        self._lock_file = open(path, "a+", encoding="ascii")
        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock_file.close()
            self._lock_file = None
            raise MotionLinkError(f"serial port is already owned: {self.port}") from exc

    def _release_port_lock(self):
        if self._lock_file is None:
            return
        if fcntl is not None:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
        self._lock_file.close()
        self._lock_file = None

    def open(self):
        if self.is_open:
            return self
        self._acquire_port_lock()
        try:
            if self._serial_factory is None:
                try:
                    import serial
                except ImportError as exc:
                    raise MotionLinkError("pyserial is not installed") from exc
                factory = serial.Serial
            else:
                factory = self._serial_factory
            self._serial = factory(
                self.port,
                self.baudrate,
                timeout=0.02,
                write_timeout=0.1,
            )
            self._running = True
            self._reader_error = None
            self._thread = threading.Thread(target=self._reader_loop,
                                            name="c5-motion-link",
                                            daemon=True)
            self._thread.start()
            return self
        except Exception:
            self._serial = None
            self._release_port_lock()
            raise

    def close(self):
        if self._serial is None:
            self._release_port_lock()
            return
        try:
            self._send_without_wait(CommandType.STOP)
        except Exception:
            pass
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        try:
            self._serial.close()
        finally:
            self._serial = None
            with self._condition:
                self._armed = False
                self._faulted = False
                self._condition.notify_all()
            self._release_port_lock()

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _next_sequence(self):
        with self._condition:
            sequence = self._sequence
            self._sequence = (self._sequence + 1) & 0xFF
            return sequence

    def _write(self, frame):
        if not self.is_open:
            raise MotionLinkError("serial link is not open")
        with self._write_lock:
            written = self._serial.write(frame)
        if written != len(frame):
            raise MotionLinkError("short serial write")

    def _send_without_wait(self, command, vx=0, vy=0, wz=0):
        sequence = self._next_sequence()
        self._write(pack_command(command, sequence, vx, vy, wz))
        return sequence

    def _transact(self, command, vx=0, vy=0, wz=0):
        sequence = self._next_sequence()
        frame = pack_command(command, sequence, vx, vy, wz)
        with self._condition:
            self._statuses.pop(sequence, None)
        self._write(frame)
        deadline = time.monotonic() + self.ack_timeout
        with self._condition:
            while sequence not in self._statuses:
                if self._reader_error is not None:
                    self._armed = False
                    self._faulted = True
                    raise MotionLinkError(f"serial reader failed: {self._reader_error}")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._armed = False
                    self._faulted = True
                    raise MotionLinkError(f"status timeout for sequence {sequence}")
                self._condition.wait(remaining)
            return self._statuses.pop(sequence)

    @staticmethod
    def _require_ok(status, operation):
        if status.result != Result.OK:
            raise MotionLinkError(f"{operation} rejected: {status.result.name}")

    def query(self):
        return self._transact(CommandType.QUERY)

    def arm(self):
        status = self._transact(CommandType.ARM)
        self._require_ok(status, "ARM")
        if status.mode != ControlMode.HOST or status.host_state != HostState.ARMED:
            raise MotionLinkError("ARM acknowledgement did not enter HOST armed state")
        with self._condition:
            self._armed = True
            self._faulted = False
        return status

    def set_twist(self, vx, vy, wz):
        with self._condition:
            if not self._armed or self._faulted:
                raise MotionLinkError("HOST is not armed")
        status = self._transact(CommandType.TWIST, vx, vy, wz)
        if status.result != Result.OK or status.host_state != HostState.ARMED:
            with self._condition:
                self._armed = False
            self._require_ok(status, "TWIST")
            raise MotionLinkError("TWIST acknowledgement disarmed HOST")
        return status

    def stop(self):
        try:
            status = self._transact(CommandType.STOP)
            self._require_ok(status, "STOP")
            return status
        finally:
            with self._condition:
                self._armed = False
                self._faulted = False

    def safe_stop(self):
        try:
            return self.stop()
        except Exception:
            with self._condition:
                self._armed = False
            return None

    def _mark_status_timeout(self, now):
        with self._condition:
            if (self._armed and self._last_status_time and
                    now - self._last_status_time > self.status_timeout):
                self._armed = False
                self._faulted = True
                self._condition.notify_all()

    def _reader_loop(self):
        try:
            while self._running:
                data = self._serial.read(64)
                now = time.monotonic()
                if not data:
                    self._mark_status_timeout(now)
                    continue
                for frame in self._parser.feed(data):
                    try:
                        status = unpack_status(frame)
                    except (ValueError, TypeError):
                        continue
                    with self._condition:
                        self._last_status = status
                        self._last_status_time = now
                        self._statuses[status.sequence] = status
                        while len(self._statuses) > 32:
                            self._statuses.popitem(last=False)
                        self._condition.notify_all()
                    if self.status_callback is not None:
                        self.status_callback(status)
        except Exception as exc:
            with self._condition:
                self._reader_error = exc
                self._armed = False
                self._faulted = True
                self._condition.notify_all()
