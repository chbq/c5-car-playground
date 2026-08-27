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


def search_config(**overrides):
    values = {
        "fov_enabled": True,
        "fov_error_alpha": 1.0,
        "fov_rate_alpha": 1.0,
        "fov_prediction_horizon": 0.0,
        "fov_predict_hold": 0.15,
        "fov_edge_enter": 0.55,
        "fov_edge_exit": 0.30,
        "fov_translation_scale": 0.25,
        "search_enabled": True,
        "search_wz": 80,
        "search_timeout": 1.5,
        "search_min_exit_error": 0.30,
        "max_vx_step": 1000,
        "max_vy_step": 1000,
        "max_wz_step": 1000,
    }
    values.update(overrides)
    return BallFollowConfig(**values)


def observation(x, height=252, confidence=0.9):
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


class BallSearchControllerTests(unittest.TestCase):
    def test_startup_without_target_never_searches(self):
        controller = BallFollowController(search_config())

        decision = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=1.0)

        self.assertEqual(decision.state, BallFollowState.NO_TARGET)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_search_latches_last_right_exit_direction(self):
        controller = BallFollowController(search_config())
        controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)

        predicted = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        searching = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.20)
        held = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.80)

        self.assertEqual(predicted.state, BallFollowState.PREDICTING)
        self.assertEqual(searching.state, BallFollowState.SEARCHING)
        self.assertEqual(searching.zone, BallFovZone.SEARCHING)
        self.assertEqual((searching.vx, searching.vy, searching.wz), (0, 0, 80))
        self.assertEqual((held.vx, held.vy, held.wz), (0, 0, 80))

        reversed_controller = BallFollowController(search_config(yaw_sign=-1))
        reversed_controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)
        reversed_search = reversed_controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.20)
        self.assertEqual(reversed_search.wz, -80)

    def test_search_latches_last_left_exit_direction(self):
        controller = BallFollowController(search_config())
        controller.update(
            180, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)

        searching = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.20)

        self.assertEqual(searching.state, BallFollowState.SEARCHING)
        self.assertEqual((searching.vx, searching.vy, searching.wz), (0, 0, -80))

    def test_center_loss_has_no_direction_evidence(self):
        controller = BallFollowController(search_config())
        controller.update(
            700, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)

        decision = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=0.20)

        self.assertEqual(decision.state, BallFollowState.NO_TARGET)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_search_stops_at_controller_timeout(self):
        controller = BallFollowController(search_config())
        controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)

        decision = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=1.50)

        self.assertEqual(decision.state, BallFollowState.NO_TARGET)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_invalid_search_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            BallFollowController(search_config(fov_enabled=False))
        with self.assertRaises(ValueError):
            BallFollowController(search_config(search_wz=261))
        with self.assertRaises(ValueError):
            BallFollowController(search_config(search_timeout=0.15))
        with self.assertRaises(ValueError):
            BallFollowController(search_config(search_timeout=10.01))

    def test_eight_second_faster_search_configuration_is_accepted(self):
        controller = BallFollowController(search_config(
            search_timeout=8.0, search_wz=100))
        controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)

        searching = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=7.99)
        stopped = controller.update(
            None, None, None, FRAME_WIDTH, FRAME_HEIGHT, now=8.0)

        self.assertEqual(searching.state, BallFollowState.SEARCHING)
        self.assertEqual(searching.wz, 100)
        self.assertEqual(stopped.state, BallFollowState.NO_TARGET)
        self.assertEqual(stopped.wz, 0)

    def test_disabled_search_does_not_constrain_existing_yaw_modes(self):
        controller = BallFollowController(BallFollowConfig(
            min_wz=40, max_wz=50, search_wz=80, search_enabled=False))
        decision = controller.update(
            1100, 252, 0.9, FRAME_WIDTH, FRAME_HEIGHT, now=0.0)
        self.assertLessEqual(abs(decision.wz), 50)


class BallSearchSessionTests(unittest.TestCase):
    @staticmethod
    def prime(session, x=1100):
        session.tick(observation(x), FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        session.tick(observation(x), FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        session.tick(observation(x), FRAME_WIDTH, FRAME_HEIGHT, now=0.10)

    def test_unconfirmed_target_never_arms_or_searches(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(search_config()),
            link=link, execute=True, acquire_cycles=3)

        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.00)
        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.05)
        decision = session.tick(
            None, FRAME_WIDTH, FRAME_HEIGHT, now=0.25)

        self.assertEqual(decision.state, BallFollowState.SEARCHING)
        self.assertEqual(link.arm_calls, 0)
        self.assertEqual(link.twists, [])

    def test_armed_search_sends_rotation_without_translation(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(search_config()),
            link=link, execute=True, acquire_cycles=3)
        self.prime(session)

        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.15)
        decision = session.tick(
            None, FRAME_WIDTH, FRAME_HEIGHT, now=0.30)

        self.assertEqual(decision.state, BallFollowState.SEARCHING)
        self.assertEqual(link.twists[-1], (0, 0, 80))
        self.assertEqual(link.stop_calls, 0)

    def test_reacquisition_requires_three_fresh_cycles(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(search_config()),
            link=link, execute=True, acquire_cycles=3)
        self.prime(session)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.15)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.30)

        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.35)
        first = link.twists[-1]
        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.40)
        second = link.twists[-1]
        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.45)
        third = link.twists[-1]

        self.assertEqual(first, (0, 0, 0))
        self.assertEqual(second, (0, 0, 0))
        self.assertNotEqual(third, (0, 0, 0))
        self.assertTrue(session.armed)

    def test_single_frame_reacquisition_does_not_extend_total_timeout(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(search_config()),
            link=link, execute=True, acquire_cycles=3)
        self.prime(session)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.15)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.30)
        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=0.80)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.85)

        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=1.66)

        self.assertTrue(session.finished)
        self.assertEqual(session.stop_reason, "search-timeout")
        self.assertEqual(link.stop_calls, 1)
        self.assertFalse(session.armed)

    def test_continuous_mode_waits_then_rearms_after_three_fresh_cycles(self):
        link = FakeLink()
        session = BallFollowSession(
            BallFollowController(search_config(
                search_timeout=8.0, search_wz=100)),
            link=link, execute=True, acquire_cycles=3,
            continuous_rearm=True)
        self.prime(session)
        self.assertEqual(link.arm_calls, 1)

        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.15)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=0.30)
        session.tick(None, FRAME_WIDTH, FRAME_HEIGHT, now=8.15)

        self.assertFalse(session.finished)
        self.assertTrue(session.waiting_for_target)
        self.assertFalse(session.armed)
        self.assertEqual(session.wait_count, 1)
        self.assertEqual(link.stop_calls, 1)

        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=8.20)
        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=8.25)
        self.assertEqual(link.arm_calls, 1)
        self.assertTrue(session.waiting_for_target)

        session.tick(observation(1100), FRAME_WIDTH, FRAME_HEIGHT, now=8.30)
        self.assertEqual(link.arm_calls, 2)
        self.assertTrue(session.armed)
        self.assertFalse(session.waiting_for_target)
        self.assertNotEqual(link.twists[-1], (0, 0, 0))

    def test_continuous_mode_requires_execute(self):
        with self.assertRaises(ValueError):
            BallFollowSession(
                BallFollowController(search_config()),
                continuous_rearm=True)


if __name__ == "__main__":
    unittest.main()
