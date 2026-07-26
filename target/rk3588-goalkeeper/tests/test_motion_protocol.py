import sys
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from motion_protocol import (  # noqa: E402
    CommandType,
    ControlMode,
    FrameParser,
    HostState,
    MotionState,
    Result,
    Status,
    crc8,
    pack_command,
    pack_status,
    unpack_status,
)


class MotionProtocolTests(unittest.TestCase):
    def test_golden_command_frames(self):
        self.assertEqual(
            pack_command(CommandType.ARM, 0x10),
            bytes.fromhex("A5 5A 01 10 00 00 00 00 00 00 C0"),
        )
        self.assertEqual(
            pack_command(CommandType.TWIST, 0x22, 100, -200, 50),
            bytes.fromhex("A5 5A 02 22 64 00 38 FF 32 00 36"),
        )

    def test_crc_and_axis_validation(self):
        self.assertEqual(crc8(bytes.fromhex("01 10 00 00 00 00 00 00")), 0xC0)
        boundary = pack_command(CommandType.TWIST, 0, -1000, 1000, -1000)
        self.assertEqual(boundary[4:10], bytes.fromhex("18 FC E8 03 18 FC"))
        with self.assertRaises(ValueError):
            pack_command(CommandType.TWIST, 0, 1001, 0, 0)
        with self.assertRaises(ValueError):
            pack_command(CommandType.TWIST, 0, -1001, 0, 0)
        with self.assertRaises(ValueError):
            pack_command(CommandType.ARM, 0, 1, 0, 0)

    def test_status_round_trip(self):
        status = Status(0x10, Result.OK, ControlMode.HOST,
                        HostState.ARMED, MotionState.STOPPED, 0)
        frame = pack_status(status)
        self.assertEqual(frame, bytes.fromhex("A5 5A 80 10 00 00 01 01 00 00 11"))
        self.assertEqual(unpack_status(frame), status)
        damaged = bytearray(frame)
        damaged[9] ^= 1
        with self.assertRaises(ValueError):
            unpack_status(bytes(damaged))

    def test_stream_resynchronization(self):
        frame = pack_status(Status(1, Result.OK, ControlMode.HOST,
                                   HostState.DISARMED, MotionState.STOPPED, 2))
        parser = FrameParser()
        self.assertEqual(parser.feed(b"\x00\xA5"), [])
        self.assertEqual(parser.feed(b"\xA5" + frame[1:6]), [])
        self.assertEqual(parser.feed(frame[6:]), [frame])


if __name__ == "__main__":
    unittest.main()
