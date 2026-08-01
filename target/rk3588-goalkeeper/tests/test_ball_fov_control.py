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
    BallFovZone,
)


FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


def fov_config(**overrides):
    values = {
        "fov_enabled": True,
        "fov_error_alpha": 1.0,
        "fov_rate_alpha": 1.0,
        "fov_prediction_horizon": 0.0,
        "fov_predict_hold": 0.15,
        "fov_edge_enter": 0.55,
        "fov_edge_exit": 0.30,
        "fov_translation_scale": 0.25,
        "max_vx_step": 1000,
        "max_vy_step": 1000,
        "max_wz_step": 1000,
    }
    values.update(overrides)
    return BallFollowConfig(**values)


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


class BallFovControllerTests(unittest.TestCase):
    def test_edge_zone_uses_exit_hysteresis(self):
        controller = BallFollowController(fov_config())
        edge = controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        held = controller.update(
            896, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        tracking = controller.update(
            768, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.10)
        center = controller.update(
            640, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.15)

        self.assertEqual(edge.zone, BallFovZone.EDGE)
        self.assertEqual(held.zone, BallFovZone.EDGE)
        self.assertEqual(tracking.zone, BallFovZone.TRACK)
        self.assertEqual(center.zone, BallFovZone.CENTER)

    def test_prediction_enters_edge_before_raw_error(self):
        controller = BallFollowController(fov_config(
            fov_prediction_horizon=0.05))
        controller.update(
            800, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        decision = controller.update(
            928, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)

        self.assertLess(abs(decision.error), 0.55)
        self.assertGreater(abs(decision.predicted_error), 0.55)
        self.assertEqual(decision.zone, BallFovZone.EDGE)

    def test_edge_reduces_translation_and_preserves_yaw_budget(self):
        common = {
            "max_vx_step": 1000,
            "max_vy_step": 1000,
            "max_wz_step": 1000,
        }
        baseline = BallFollowController(BallFollowConfig(**common)).update(
            1100, 72, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        protected = BallFollowController(fov_config()).update(
            1100, 72, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)

        baseline_translation = abs(baseline.vx) + abs(baseline.vy)
        protected_translation = abs(protected.vx) + abs(protected.vy)
        self.assertEqual(protected.zone, BallFovZone.EDGE)
        self.assertLess(protected_translation, baseline_translation)
        self.assertGreaterEqual(abs(protected.wz), abs(baseline.wz))
        self.assertLessEqual(
            abs(protected.vx) + abs(protected.vy) + abs(protected.wz),
            1000)

    def test_repeated_edge_updates_do_not_decay_translation(self):
        controller = BallFollowController(fov_config())
        first = controller.update(
            1100, 72, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        second = controller.update(
            1100, 72, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)

        self.assertEqual((second.vx, second.vy), (first.vx, first.vy))
        self.assertNotEqual((second.vx, second.vy), (0, 0))

    def test_short_loss_predicts_yaw_only_then_stops(self):
        controller = BallFollowController(fov_config())
        controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        predicted = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        expired = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.16)
        still_missing = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.21)

        self.assertEqual(predicted.state, BallFollowState.PREDICTING)
        self.assertEqual(predicted.zone, BallFovZone.PREDICTING)
        self.assertTrue(predicted.predicted_only)
        self.assertEqual((predicted.vx, predicted.vy), (0, 0))
        self.assertGreater(predicted.wz, 0)
        self.assertAlmostEqual(predicted.target_age, 0.05)
        self.assertEqual(expired.state, BallFollowState.NO_TARGET)
        self.assertEqual((expired.vx, expired.vy, expired.wz), (0, 0, 0))
        self.assertEqual(expired.lost_frames, 2)
        self.assertEqual(still_missing.lost_frames, 3)

    def test_invalid_fov_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            BallFollowController(fov_config(
                fov_edge_exit=0.6, fov_edge_enter=0.5))
        with self.assertRaises(ValueError):
            BallFollowController(fov_config(fov_predict_hold=0.21))


class BallFovSessionTests(unittest.TestCase):
    def test_armed_session_sends_predicted_yaw_without_translation(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(fov_config()),
            link=link,
            execute=True,
            acquire_cycles=1,
            lost_timeout=1.5,
            hold_arm_until_duration=True,
        )

        session.tick(
            observation(1100, height=252),
            FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        predicted_twist = link.twists[-1]
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.20)

        self.assertEqual(link.arm_calls, 1)
        self.assertEqual(predicted_twist[:2], (0, 0))
        self.assertGreater(predicted_twist[2], 0)
        self.assertEqual(link.twists[-1], (0, 0, 0))
        self.assertEqual(link.stop_calls, 0)


if __name__ == "__main__":
    unittest.main()
