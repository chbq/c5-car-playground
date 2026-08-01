import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from ball_follow_control import (  # noqa: E402
    BallFollowConfig,
    BallFollowController,
    BallFollowSession,
    BallFollowState,
)


FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


def observation(x, height=72, confidence=0.9):
    return SimpleNamespace(
        x=x, y=360, width=height, height=height,
        conf=confidence, ts=0.0)


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


class BallFollowControllerTests(unittest.TestCase):
    def test_defaults_cover_all_camera_axes(self):
        config = BallFollowConfig()
        self.assertEqual(config.max_vx, 800)
        self.assertEqual(config.max_vy, 600)
        self.assertEqual(config.max_wz, 180)
        self.assertEqual(config.target_box_ratio, 0.35)

    def test_right_ball_requests_negative_vx_and_positive_wz(self):
        config = BallFollowConfig(max_vx_step=1000, max_wz_step=1000)
        decision = BallFollowController(config).update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertEqual(decision.state, BallFollowState.TRACKING)
        self.assertLess(decision.vx, 0)
        self.assertEqual(decision.vy, 0)
        self.assertGreater(decision.wz, 0)

    def test_left_ball_requests_positive_vx_and_negative_wz(self):
        config = BallFollowConfig(max_vx_step=1000, max_wz_step=1000)
        decision = BallFollowController(config).update(
            180, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertEqual(decision.state, BallFollowState.TRACKING)
        self.assertGreater(decision.vx, 0)
        self.assertEqual(decision.vy, 0)
        self.assertLess(decision.wz, 0)

    def test_centered_ball_stops_both_axes(self):
        config = BallFollowConfig(max_vx_step=1000, max_wz_step=1000)
        decision = BallFollowController(config).update(
            640, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertEqual(decision.state, BallFollowState.CENTERED)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_box_distance_requests_symmetric_vy(self):
        config = BallFollowConfig(max_vy_step=1000)
        far = BallFollowController(config).update(
            640, 72, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        near = BallFollowController(config).update(
            640, 432, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertGreater(far.vy, 0)
        self.assertLess(near.vy, 0)
        self.assertEqual((far.vx, far.wz), (0, 0))
        self.assertEqual((near.vx, near.wz), (0, 0))

    def test_three_axis_output_is_limited_before_transport(self):
        config = BallFollowConfig(
            max_vx_step=1000, max_vy_step=1000, max_wz_step=1000)
        decision = BallFollowController(config).update(
            1280, 10, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertLessEqual(
            abs(decision.vx) + abs(decision.vy) + abs(decision.wz), 1000)

    def test_vx_sign_reversal_crosses_zero(self):
        config = BallFollowConfig(max_vx_step=1000, max_wz_step=1000)
        controller = BallFollowController(config)
        right = controller.update(1000, 100, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        crossing = controller.update(200, 100, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        left = controller.update(200, 100, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertLess(right.vx, 0)
        self.assertEqual(crossing.vx, 0)
        self.assertGreater(left.vx, 0)

    def test_target_loss_and_bad_box_stop_immediately(self):
        controller = BallFollowController(BallFollowConfig(max_vx_step=1000))
        controller.update(640, 36, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        missing = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT)
        bad_box = controller.update(
            640, 0, 0.9, FRAME_WIDTH, FRAME_HEIGHT)
        low = controller.update(
            640, 36, 0.2, FRAME_WIDTH, FRAME_HEIGHT)
        self.assertEqual(missing.state, BallFollowState.NO_TARGET)
        self.assertEqual(bad_box.state, BallFollowState.NO_TARGET)
        self.assertEqual(low.state, BallFollowState.LOW_CONFIDENCE)
        self.assertEqual((missing.vx, missing.wz), (0, 0))
        self.assertEqual((bad_box.vx, bad_box.wz), (0, 0))
        self.assertEqual((low.vx, low.wz), (0, 0))

    def test_invalid_configuration_and_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            BallFollowController(BallFollowConfig(max_vx=1001))
        with self.assertRaises(ValueError):
            BallFollowController(BallFollowConfig(vx_gain=0))
        with self.assertRaises(ValueError):
            BallFollowController(BallFollowConfig(target_box_ratio=0))
        with self.assertRaises(ValueError):
            BallFollowController(BallFollowConfig(vy_gain=0))
        with self.assertRaises(ValueError):
            BallFollowController().update(10, 10, 0.9, 0, FRAME_HEIGHT)


class BallFollowSessionTests(unittest.TestCase):
    def test_dry_run_never_arms(self):
        session = BallFollowSession(BallFollowController(), execute=False)
        decision = session.tick(
            observation(640, height=252), FRAME_WIDTH, FRAME_HEIGHT, now=0.0)
        self.assertEqual(decision.state, BallFollowState.CENTERED)
        self.assertFalse(session.armed)

    def test_execute_sends_vx_vy_and_wz(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(), link=link, execute=True, acquire_cycles=3)
        session.tick(observation(800), FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        session.tick(observation(800), FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        session.tick(observation(800), FRAME_WIDTH, FRAME_HEIGHT, now=0.10)
        vx, vy, wz = link.twists[-1]
        self.assertLess(vx, 0)
        self.assertGreater(vy, 0)
        self.assertGreater(wz, 0)
        self.assertEqual(link.arm_calls, 1)

    def test_target_loss_holds_zero_and_reacquires(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(), link=link, execute=True,
            acquire_cycles=2, lost_timeout=0.5,
            hold_arm_until_duration=True)
        session.tick(observation(800), FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        session.tick(observation(800), FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.10)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.55)
        self.assertTrue(session.paused)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        count = len(link.twists)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.60)
        self.assertEqual(len(link.twists), count + 1)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        session.tick(
            observation(200), FRAME_WIDTH, FRAME_HEIGHT, now=0.65)
        session.tick(
            observation(200), FRAME_WIDTH, FRAME_HEIGHT, now=0.70)
        self.assertGreater(link.twists[-1][0], 0)
        self.assertGreater(link.twists[-1][1], 0)
        self.assertEqual(link.arm_calls, 1)

    def test_stop_is_idempotent(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(), link=link, execute=True, acquire_cycles=1)
        session.tick(observation(640), FRAME_WIDTH, FRAME_HEIGHT, now=0.0)
        session.stop("duration")
        session.stop("again")
        self.assertEqual(link.stop_calls, 1)
        self.assertEqual(session.stop_reason, "duration")


if __name__ == "__main__":
    unittest.main()
