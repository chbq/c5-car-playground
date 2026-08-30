import sys
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from zdt_pusher_control import (  # noqa: E402
    PusherCycleConfig,
    run_bounded_cycles,
)
from zdt_pusher_link import PusherLinkError  # noqa: E402
from zdt_pusher_protocol import MotorStatus  # noqa: E402


def status(reached=True, stalled=False, protected=False):
    return MotorStatus(
        raw=0,
        enabled=True,
        reached=reached,
        stalled=stalled,
        stall_protected=protected,
        left_limit_high=False,
        right_limit_high=False,
        power_lost=False,
    )


class FakeLink:
    def __init__(self, statuses=None):
        self.statuses = list(statuses or [])
        self.calls = []

    def query_status(self):
        self.calls.append(("query",))
        return self.statuses.pop(0) if self.statuses else status()

    def set_enabled(self, enabled):
        self.calls.append(("enable", enabled))

    def move_relative(self, direction, speed, acceleration, pulses):
        self.calls.append(("move", direction, speed, acceleration, pulses))

    def safe_stop(self):
        self.calls.append(("stop",))
        return True

    def safe_disable(self):
        self.calls.append(("disable",))
        return True


class EnableAckLostLink(FakeLink):
    def set_enabled(self, enabled):
        super().set_enabled(enabled)
        raise PusherLinkError("enable acknowledgement lost")


def config(idle_behavior="hold"):
    return PusherCycleConfig(
        stroke_pulses=200,
        speed_rpm=100,
        acceleration=10,
        cycles=2,
        outward_direction=1,
        segment_timeout=1.0,
        idle_behavior=idle_behavior,
    )


class ZdtPusherControlTests(unittest.TestCase):
    def test_two_cycles_alternate_and_finish_with_stop_hold(self):
        link = FakeLink()
        result = run_bounded_cycles(link, config())
        moves = [call for call in link.calls if call[0] == "move"]
        self.assertEqual([call[1] for call in moves], [1, 0, 1, 0])
        self.assertEqual(result.completed_cycles, 2)
        self.assertTrue(result.holding)
        self.assertEqual(link.calls[-1], ("stop",))
        self.assertNotIn(("disable",), link.calls)

    def test_release_is_explicit_and_occurs_after_stop(self):
        link = FakeLink()
        result = run_bounded_cycles(link, config("release"))
        self.assertFalse(result.holding)
        self.assertEqual(link.calls[-2:], [("stop",), ("disable",)])

    def test_stall_stops_without_continuing(self):
        link = FakeLink([status(), status(stalled=True)])
        with self.assertRaisesRegex(PusherLinkError, "stall"):
            run_bounded_cycles(link, config())
        self.assertEqual(link.calls[-1], ("stop",))
        self.assertEqual(len([c for c in link.calls if c[0] == "move"]), 1)

    def test_preexisting_stall_stops_before_enable(self):
        link = FakeLink([status(protected=True)])
        with self.assertRaisesRegex(PusherLinkError, "before cycle"):
            run_bounded_cycles(link, config())
        self.assertNotIn(("enable", True), link.calls)
        self.assertEqual(link.calls[-1], ("stop",))

    def test_enable_ack_loss_still_attempts_stop(self):
        link = EnableAckLostLink()
        with self.assertRaisesRegex(PusherLinkError, "acknowledgement"):
            run_bounded_cycles(link, config())
        self.assertEqual(link.calls[-1], ("stop",))

    def test_hardware_unverified_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            PusherCycleConfig(
                3201, 100, 10, 1, 0, 1.0,
                idle_behavior="hold").validate()
        with self.assertRaises(ValueError):
            PusherCycleConfig(
                100, 301, 10, 1, 0, 1.0,
                idle_behavior="hold").validate()
        with self.assertRaises(ValueError):
            PusherCycleConfig(
                100, 100, 10, 1, 0, 1.0,
                idle_behavior="").validate()


if __name__ == "__main__":
    unittest.main()
