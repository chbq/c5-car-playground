import sys
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from zdt_pusher_protocol import (  # noqa: E402
    CODE_ENABLE,
    MotorStatus,
    PusherProtocolError,
    pack_enable,
    pack_relative_position,
    pack_status_query,
    pack_stop,
    parse_ack,
    parse_motor_status,
)


class ZdtPusherProtocolTests(unittest.TestCase):
    def test_vendor_default_frames_are_exact(self):
        self.assertEqual(pack_status_query(), bytes.fromhex("01 3A 6B"))
        self.assertEqual(
            pack_enable(True), bytes.fromhex("01 F3 AB 01 00 6B"))
        self.assertEqual(
            pack_enable(False), bytes.fromhex("01 F3 AB 00 00 6B"))
        self.assertEqual(pack_stop(), bytes.fromhex("01 FE 98 00 6B"))
        self.assertEqual(
            pack_relative_position(1, 1500, 10, 32000),
            bytes.fromhex("01 FD 01 05 DC 0A 00 00 7D 00 02 00 6B"),
        )

    def test_status_flags_decode_independently(self):
        status = parse_motor_status(bytes.fromhex("01 3A BF 6B"))
        self.assertEqual(
            status,
            MotorStatus(
                raw=0xBF,
                enabled=True,
                reached=True,
                stalled=True,
                stall_protected=True,
                left_limit_high=True,
                right_limit_high=True,
                power_lost=True,
            ),
        )

    def test_ack_rejects_motor_error_and_wrong_suffix(self):
        with self.assertRaisesRegex(PusherProtocolError, "PARAMETER_ERROR"):
            parse_ack(bytes.fromhex("01 F3 E2 6B"), CODE_ENABLE)
        with self.assertRaisesRegex(PusherProtocolError, "check byte"):
            parse_ack(bytes.fromhex("01 F3 02 00"), CODE_ENABLE)

    def test_motion_ranges_and_broadcast_are_rejected(self):
        with self.assertRaises(PusherProtocolError):
            pack_status_query(0)
        with self.assertRaises(PusherProtocolError):
            pack_relative_position(0, 0, 10, 100)
        with self.assertRaises(PusherProtocolError):
            pack_relative_position(0, 100, 10, 0)


if __name__ == "__main__":
    unittest.main()
