import sys
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from zdt_pusher_link import PusherLinkError, ZdtPusherLink  # noqa: E402


class FakeSerial:
    def __init__(self, port, baudrate, timeout, write_timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.is_open = True
        self.respond = True
        self.writes = []
        self.rx = bytearray()

    def reset_input_buffer(self):
        self.rx.clear()

    def write(self, frame):
        frame = bytes(frame)
        self.writes.append(frame)
        if self.respond:
            if frame[1] == 0x3A:
                self.rx.extend(bytes.fromhex("01 3A 03 6B"))
            else:
                self.rx.extend(bytes((0x01, frame[1], 0x02, 0x6B)))
        return len(frame)

    def read(self, size):
        data = bytes(self.rx[:size])
        del self.rx[:size]
        return data

    def close(self):
        self.is_open = False


class ZdtPusherLinkTests(unittest.TestCase):
    def make_link(self, timeout=0.03):
        serial = None

        def factory(*args, **kwargs):
            nonlocal serial
            serial = FakeSerial(*args, **kwargs)
            return serial

        link = ZdtPusherLink(
            "/dev/c5-pusher", timeout=timeout,
            serial_factory=factory, lock_path=None)
        link.open()
        return link, lambda: serial

    def test_explicit_port_is_required(self):
        with self.assertRaisesRegex(ValueError, "explicit"):
            ZdtPusherLink("auto")
        with self.assertRaisesRegex(ValueError, "explicit"):
            ZdtPusherLink("")

    def test_query_enable_move_stop_and_release(self):
        link, get_serial = self.make_link()
        try:
            status = link.query_status()
            self.assertTrue(status.enabled)
            self.assertTrue(status.reached)
            link.set_enabled(True)
            link.move_relative(0, 100, 10, 200)
            link.stop()
            link.set_enabled(False)
            self.assertEqual(
                get_serial().writes,
                [
                    bytes.fromhex("01 3A 6B"),
                    bytes.fromhex("01 F3 AB 01 00 6B"),
                    bytes.fromhex(
                        "01 FD 00 00 64 0A 00 00 00 C8 02 00 6B"),
                    bytes.fromhex("01 FE 98 00 6B"),
                    bytes.fromhex("01 F3 AB 00 00 6B"),
                ],
            )
        finally:
            link.close()

    def test_query_only_close_sends_no_stop(self):
        link, get_serial = self.make_link()
        link.query_status()
        link.close()
        self.assertEqual(get_serial().writes, [bytes.fromhex("01 3A 6B")])

    def test_timeout_is_reported(self):
        link, get_serial = self.make_link()
        try:
            get_serial().respond = False
            with self.assertRaisesRegex(PusherLinkError, "timeout"):
                link.query_status()
        finally:
            link.close()


if __name__ == "__main__":
    unittest.main()
