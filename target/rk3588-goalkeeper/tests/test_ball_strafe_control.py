import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from ball_strafe_control import (  # noqa: E402
    BallStrafeConfig,
    BallStrafeController,
    BallStrafeSession,
    BallStrafeState,
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


class BallStrafeControllerTests(unittest.TestCase):
    def test_default_parameters_are_aggressive_but_bounded(self):
        config = BallStrafeConfig()
        self.assertEqual(config.min_vy, 250)
        self.assertEqual(config.max_vy, 800)
        self.assertEqual(config.proportional_gain, 1000.0)
        self.assertEqual(config.max_step, 120)
        self.assertEqual(config.lateral_sign, -1)

    def test_positive_sign_maps_image_right_to_positive_vy(self):
        controller = BallStrafeController(
            BallStrafeConfig(lateral_sign=1, max_step=1000))
        center = controller.update(640, 0.9, 1280)
        right = controller.update(1280, 0.9, 1280)
        controller.reset()
        left = controller.update(0, 0.9, 1280)
        self.assertEqual(center.state, BallStrafeState.CENTERED)
        self.assertEqual(center.vy, 0)
        self.assertEqual(right.vy, 800)
        self.assertEqual(left.vy, -800)

    def test_minimum_limit_slew_and_sign_reversal(self):
        controller = BallStrafeController(BallStrafeConfig(lateral_sign=1))
        first = controller.update(720, 0.9, 1280)
        second = controller.update(720, 0.9, 1280)
        reversed_direction = controller.update(500, 0.9, 1280)
        self.assertEqual(first.vy, 120)
        self.assertEqual(second.vy, 240)
        self.assertEqual(reversed_direction.vy, 0)

    def test_low_confidence_and_missing_target_stop_immediately(self):
        controller = BallStrafeController(BallStrafeConfig(max_step=1000))
        self.assertNotEqual(controller.update(1000, 0.9, 1280).vy, 0)
        low = controller.update(1000, 0.2, 1280)
        missing = controller.update(None, None, 1280)
        self.assertEqual(low.state, BallStrafeState.LOW_CONFIDENCE)
        self.assertEqual(low.vy, 0)
        self.assertEqual(missing.state, BallStrafeState.NO_TARGET)
        self.assertEqual(missing.vy, 0)

    def test_default_c5_sign_reverses_image_error(self):
        controller = BallStrafeController(BallStrafeConfig(max_step=1000))
        self.assertLess(controller.update(1000, 0.9, 1280).vy, 0)
        with self.assertRaises(ValueError):
            BallStrafeController(BallStrafeConfig(max_vy=1001))
        with self.assertRaises(ValueError):
            BallStrafeController().update(10, 0.9, 0)


class BallStrafeSessionTests(unittest.TestCase):
    def test_dry_run_never_arms(self):
        session = BallStrafeSession(BallStrafeController(), execute=False)
        decision = session.tick(observation(1000), 1280, now=0.0)
        self.assertEqual(decision.state, BallStrafeState.TRACKING)
        self.assertFalse(session.armed)

    def test_execute_arms_after_three_targets_and_sends_only_vy(self):
        link = FakeLink()
        session = BallStrafeSession(
            BallStrafeController(BallStrafeConfig(lateral_sign=1)),
            link=link, execute=True, acquire_cycles=3)
        session.tick(observation(1000), 1280, now=0.00)
        session.tick(observation(1000), 1280, now=0.05)
        self.assertEqual(link.arm_calls, 0)
        session.tick(observation(1000), 1280, now=0.10)
        self.assertEqual(link.arm_calls, 1)
        self.assertEqual(link.twists[-1][0], 0)
        self.assertGreater(link.twists[-1][1], 0)
        self.assertEqual(link.twists[-1][2], 0)

    def test_target_loss_sends_zero_then_stops(self):
        link = FakeLink()
        session = BallStrafeSession(
            BallStrafeController(BallStrafeConfig(max_step=1000)),
            link=link, execute=True, acquire_cycles=1, lost_timeout=0.5)
        session.tick(observation(1000), 1280, now=0.0)
        session.tick(None, 1280, now=0.1)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        session.tick(None, 1280, now=0.5)
        self.assertTrue(session.finished)
        self.assertEqual(session.stop_reason, "target-lost")
        self.assertEqual(link.stop_calls, 1)
        self.assertFalse(session.armed)

    def test_hold_mode_refreshes_zero_and_reacquires(self):
        link = FakeLink()
        session = BallStrafeSession(
            BallStrafeController(BallStrafeConfig(max_step=1000)),
            link=link, execute=True, acquire_cycles=2, lost_timeout=0.5,
            hold_arm_until_duration=True)
        session.tick(observation(1000), 1280, now=0.00)
        session.tick(observation(1000), 1280, now=0.05)
        session.tick(None, 1280, now=0.10)
        session.tick(None, 1280, now=0.55)
        self.assertTrue(session.armed)
        self.assertTrue(session.paused)
        zero_count = len(link.twists)
        session.tick(None, 1280, now=0.60)
        self.assertEqual(len(link.twists), zero_count + 1)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        session.tick(observation(200), 1280, now=0.65)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        session.tick(observation(200), 1280, now=0.70)
        self.assertGreater(link.twists[-1][1], 0)
        self.assertEqual(link.arm_calls, 1)
        session.stop("duration")
        self.assertEqual(link.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
