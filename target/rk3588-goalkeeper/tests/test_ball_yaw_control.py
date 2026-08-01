import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from ball_yaw_control import (  # noqa: E402
    BallYawConfig,
    BallYawController,
    BallYawSession,
    BallYawState,
)
def observation(x, confidence=0.9, timestamp=0.0):
    return SimpleNamespace(x=x, y=360, conf=confidence, ts=timestamp)


class FakeLink:
    def __init__(self):
        self.arm_calls = 0
        self.twists = []
        self.stop_calls = 0

    def arm(self):
        self.arm_calls += 1

    def set_twist(self, vx, vy, wz):
        self.twists.append((vx, vy, wz))

    def safe_stop(self):
        self.stop_calls += 1


class BallYawControllerTests(unittest.TestCase):
    def test_center_and_deadband_stop(self):
        controller = BallYawController()
        center = controller.update(640, 0.9, 1280)
        edge = controller.update(690, 0.9, 1280)
        self.assertEqual(center.state, BallYawState.CENTERED)
        self.assertEqual(center.wz, 0)
        self.assertEqual(edge.state, BallYawState.CENTERED)
        self.assertEqual(edge.wz, 0)

    def test_right_is_positive_clockwise_and_left_is_negative(self):
        config = BallYawConfig(max_step=1000)
        controller = BallYawController(config)
        right = controller.update(1280, 0.9, 1280)
        controller.reset()
        left = controller.update(0, 0.9, 1280)
        self.assertEqual(right.wz, 100)
        self.assertEqual(left.wz, -100)

    def test_yaw_sign_can_be_reversed(self):
        config = BallYawConfig(yaw_sign=-1, max_step=1000)
        decision = BallYawController(config).update(1000, 0.9, 1280)
        self.assertLess(decision.wz, 0)

    def test_minimum_limit_slew_and_sign_reversal(self):
        controller = BallYawController(BallYawConfig(max_step=20))
        first = controller.update(700, 0.9, 1280)
        second = controller.update(700, 0.9, 1280)
        reversed_direction = controller.update(500, 0.9, 1280)
        self.assertEqual(first.wz, 20)
        self.assertEqual(second.wz, 40)
        self.assertEqual(reversed_direction.wz, 0)

    def test_low_confidence_and_missing_target_stop_immediately(self):
        controller = BallYawController(BallYawConfig(max_step=1000))
        self.assertNotEqual(controller.update(1000, 0.9, 1280).wz, 0)
        low = controller.update(1000, 0.4, 1280)
        missing = controller.update(None, None, 1280)
        self.assertEqual(low.state, BallYawState.LOW_CONFIDENCE)
        self.assertEqual(low.wz, 0)
        self.assertEqual(missing.state, BallYawState.NO_TARGET)
        self.assertEqual(missing.wz, 0)

    def test_invalid_configuration_and_width_are_rejected(self):
        with self.assertRaises(ValueError):
            BallYawController(BallYawConfig(yaw_sign=0))
        with self.assertRaises(ValueError):
            BallYawController().update(10, 0.9, 0)


class BallYawSessionTests(unittest.TestCase):
    def test_dry_run_never_uses_link(self):
        session = BallYawSession(BallYawController(), execute=False)
        decision = session.tick(observation(1000), 1280, now=0.0)
        self.assertEqual(decision.state, BallYawState.TRACKING)
        self.assertFalse(session.armed)

    def test_execute_waits_for_consecutive_targets_then_arms(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(), link=link, execute=True, acquire_cycles=3)
        session.tick(observation(1000), 1280, now=0.00)
        session.tick(observation(1000), 1280, now=0.05)
        self.assertEqual(link.arm_calls, 0)
        session.tick(observation(1000), 1280, now=0.10)
        self.assertEqual(link.arm_calls, 1)
        self.assertTrue(session.armed)
        self.assertEqual(len(link.twists), 1)
        self.assertEqual(link.twists[0][:2], (0, 0))
        self.assertEqual(session.last_sent_wz, link.twists[0][2])

    def test_control_rate_is_limited_to_twenty_hz(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(), link=link, execute=True, acquire_cycles=1)
        self.assertIsNotNone(
            session.tick(observation(1000), 1280, now=0.000))
        self.assertIsNone(
            session.tick(observation(1000), 1280, now=0.020))
        self.assertIsNotNone(
            session.tick(observation(1000), 1280, now=0.050))
        self.assertEqual(len(link.twists), 2)

    def test_missing_target_sends_zero_then_stops_and_disarms(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(BallYawConfig(max_step=1000)),
            link=link, execute=True, acquire_cycles=1, lost_timeout=0.5)
        session.tick(observation(1000), 1280, now=0.0)
        session.tick(None, 1280, now=0.1)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        self.assertEqual(session.last_sent_wz, 0)
        self.assertFalse(session.finished)
        session.tick(None, 1280, now=0.5)
        self.assertTrue(session.finished)
        self.assertEqual(session.stop_reason, "target-lost")
        self.assertEqual(link.stop_calls, 1)
        self.assertFalse(session.armed)
        self.assertEqual(session.last_sent_wz, 0)

    def test_reacquired_target_is_confirmed_before_motion_resumes(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(BallYawConfig(max_step=1000)),
            link=link, execute=True, acquire_cycles=2, lost_timeout=0.5)
        session.tick(observation(1000), 1280, now=0.00)
        session.tick(observation(1000), 1280, now=0.05)
        self.assertNotEqual(link.twists[-1][2], 0)
        session.tick(None, 1280, now=0.10)
        session.tick(observation(1000), 1280, now=0.15)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        session.tick(observation(1000), 1280, now=0.20)
        self.assertNotEqual(link.twists[-1][2], 0)

    def test_explicit_stop_is_idempotent(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(), link=link, execute=True, acquire_cycles=1)
        session.tick(observation(1000), 1280, now=0.0)
        session.stop("duration")
        session.stop("again")
        self.assertEqual(link.stop_calls, 1)
        self.assertEqual(session.stop_reason, "duration")

    def test_explicit_hold_mode_keeps_arm_until_duration(self):
        link = FakeLink()
        session = BallYawSession(
            BallYawController(BallYawConfig(max_step=1000)),
            link=link, execute=True, acquire_cycles=2, lost_timeout=0.5,
            hold_arm_until_duration=True)
        session.tick(observation(1000), 1280, now=0.00)
        session.tick(observation(1000), 1280, now=0.05)
        self.assertEqual(link.arm_calls, 1)
        session.tick(None, 1280, now=0.10)
        session.tick(None, 1280, now=0.55)
        self.assertFalse(session.finished)
        self.assertTrue(session.paused)
        self.assertTrue(session.armed)
        self.assertEqual(session.pause_count, 1)
        self.assertEqual(link.stop_calls, 0)
        self.assertEqual(session.last_sent_wz, 0)
        zero_count = len(link.twists)
        session.tick(None, 1280, now=0.60)
        self.assertEqual(len(link.twists), zero_count + 1)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        self.assertTrue(session.armed)
        session.tick(observation(200), 1280, now=0.65)
        self.assertTrue(session.armed)
        self.assertTrue(session.paused)
        session.tick(observation(200), 1280, now=0.70)
        self.assertTrue(session.armed)
        self.assertFalse(session.paused)
        self.assertEqual(link.arm_calls, 1)
        self.assertLess(link.twists[-1][2], 0)
        session.stop("duration")
        self.assertFalse(session.armed)
        self.assertEqual(link.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
