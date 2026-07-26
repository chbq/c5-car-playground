import sys
from pathlib import Path
import threading
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from motion_link import MotionLink, MotionLinkError  # noqa: E402
from motion_protocol import (  # noqa: E402
    CommandType,
    ControlMode,
    HostState,
    MotionState,
    Result,
    Status,
    pack_status,
)


class FakeSerial:
    def __init__(self, port, baudrate, timeout, write_timeout):
        self.timeout = timeout
        self.is_open = True
        self.respond = True
        self.armed = False
        self._rx = bytearray()
        self._condition = threading.Condition()

    def write(self, frame):
        command = frame[2]
        sequence = frame[3]
        result = Result.OK
        motion = MotionState.STOPPED
        if command == CommandType.ARM:
            self.armed = True
        elif command == CommandType.TWIST:
            if not self.armed:
                result = Result.NOT_ARMED
            elif any(frame[index:index + 2] != b"\x00\x00" for index in (4, 6, 8)):
                motion = MotionState.MOVING
        elif command == CommandType.STOP:
            self.armed = False
        if self.respond:
            status = Status(sequence, result, ControlMode.HOST,
                            HostState.ARMED if self.armed else HostState.DISARMED,
                            motion, 0)
            with self._condition:
                self._rx.extend(pack_status(status))
                self._condition.notify_all()
        return len(frame)

    def read(self, size):
        deadline = time.monotonic() + self.timeout
        with self._condition:
            while not self._rx and self.is_open:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return b""
                self._condition.wait(remaining)
            data = bytes(self._rx[:size])
            del self._rx[:size]
            return data

    def close(self):
        with self._condition:
            self.is_open = False
            self._condition.notify_all()


class MotionLinkTests(unittest.TestCase):
    def make_link(self, ack_timeout=0.1, status_timeout=0.1):
        fake = None

        def factory(*args, **kwargs):
            nonlocal fake
            fake = FakeSerial(*args, **kwargs)
            return fake

        link = MotionLink("fake", serial_factory=factory, lock_path=None,
                          ack_timeout=ack_timeout,
                          status_timeout=status_timeout)
        link.open()
        return link, lambda: fake

    def test_arm_twist_stop(self):
        link, get_fake = self.make_link()
        try:
            self.assertEqual(link.query().motion_state, MotionState.STOPPED)
            self.assertEqual(link.arm().host_state, HostState.ARMED)
            self.assertTrue(link.is_armed)
            self.assertEqual(link.set_twist(100, -50, 25).motion_state,
                             MotionState.MOVING)
            self.assertEqual(link.stop().host_state, HostState.DISARMED)
            self.assertFalse(link.is_armed)
            self.assertIsNotNone(get_fake())
        finally:
            link.close()

    def test_ack_timeout_disarms(self):
        link, get_fake = self.make_link(ack_timeout=0.03)
        try:
            get_fake().respond = False
            with self.assertRaises(MotionLinkError):
                link.arm()
            self.assertFalse(link.is_armed)
        finally:
            link.close()

    def test_status_watchdog_disarms(self):
        link, get_fake = self.make_link(status_timeout=0.04)
        try:
            link.arm()
            get_fake().respond = False
            time.sleep(0.09)
            self.assertFalse(link.is_armed)
            with self.assertRaises(MotionLinkError):
                link.set_twist(10, 0, 0)
        finally:
            link.close()


if __name__ == "__main__":
    unittest.main()
