import sys
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from goalkeeper_policy import (  # noqa: E402
    BallRange,
    GoalkeeperConfig,
    GoalkeeperPolicy,
    GoalkeeperState,
    LocalizationCapability,
    MotionIntent,
    PerceptionFrame,
    PusherIntent,
    VisualObservation,
)


WIDTH = 1280
HEIGHT = 720


def observation(x=640, width=50, height=50, confidence=0.9, now=0.0):
    return VisualObservation(
        x=x, y=360, width=width, height=height,
        confidence=confidence, captured_at=now)


def frame(frame_id, now, ball=None, goal=None):
    return PerceptionFrame(
        frame_id=frame_id,
        captured_at=now,
        processed_at=now,
        frame_width=WIDTH,
        frame_height=HEIGHT,
        ball=ball,
        opponent_goal=goal,
    )


def anchor(policy, now=0.0, x=640):
    decision = None
    for index in range(3):
        ts = now + index * 0.05
        decision = policy.update(
            frame(index, ts, goal=observation(x=x, now=ts)), enabled=True)
    return decision


class GoalkeeperPolicyTests(unittest.TestCase):
    def test_disabled_is_zero_and_invalid(self):
        policy = GoalkeeperPolicy()
        decision = policy.update(
            frame(0, 0.0, goal=observation()),
            MotionIntent(200, 200, 100), enabled=False)
        self.assertEqual(decision.state, GoalkeeperState.DISABLED)
        self.assertEqual(decision.capability, LocalizationCapability.INVALID)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))
        self.assertEqual(decision.pusher, PusherIntent.IDLE)

    def test_goal_requires_three_fresh_cycles_before_hold(self):
        policy = GoalkeeperPolicy()
        first = policy.update(
            frame(0, 0.0, goal=observation(now=0.0)), enabled=True)
        second = policy.update(
            frame(1, 0.05, goal=observation(now=0.05)), enabled=True)
        third = policy.update(
            frame(2, 0.10, goal=observation(now=0.10)), enabled=True)
        self.assertEqual(first.state, GoalkeeperState.ANCHORING)
        self.assertEqual(second.state, GoalkeeperState.ANCHORING)
        self.assertEqual(third.state, GoalkeeperState.HOLD)
        self.assertEqual(third.capability, LocalizationCapability.GOAL_RELATIVE)

    def test_far_ball_allows_yaw_only(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        decision = policy.update(
            frame(3, 0.15, ball=observation(
                x=900, width=30, height=30, now=0.15),
                goal=observation(now=0.15)),
            MotionIntent(-200, 180, 90), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.BALL_WATCH)
        self.assertEqual(decision.ball_range, BallRange.FAR)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 90))

    def test_warning_ball_allows_bounded_signed_three_axis_intent(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        decision = policy.update(
            frame(3, 0.15, ball=observation(
                x=1000, width=50, height=50, now=0.15),
                goal=observation(now=0.15)),
            MotionIntent(-700, 600, 400), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.INTERCEPT)
        self.assertEqual(decision.ball_range, BallRange.WARNING)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (-300, 250, 180))

    def test_close_ball_stops_chassis_and_requests_pusher(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        decision = policy.update(
            frame(3, 0.15, ball=observation(
                width=100, height=90, now=0.15),
                goal=observation(now=0.15)),
            MotionIntent(300, 250, 180), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.CLOSE_BLOCK)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))
        self.assertEqual(decision.pusher, PusherIntent.CYCLE)

    def test_ball_range_uses_exit_hysteresis(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        warning = policy.update(
            frame(3, 0.15, ball=observation(
                width=40, height=40, now=0.15),
                goal=observation(now=0.15)), enabled=True)
        held = policy.update(
            frame(4, 0.20, ball=observation(
                width=35, height=40, now=0.20),
                goal=observation(now=0.20)), enabled=True)
        far = policy.update(
            frame(5, 0.25, ball=observation(
                width=29, height=40, now=0.25),
                goal=observation(now=0.25)), enabled=True)
        self.assertEqual(warning.ball_range, BallRange.WARNING)
        self.assertEqual(held.ball_range, BallRange.WARNING)
        self.assertEqual(far.ball_range, BallRange.FAR)

    def test_goal_soft_limit_overrides_ball_translation(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        decision = policy.update(
            frame(3, 0.15, ball=observation(
                width=50, height=50, now=0.15),
                goal=observation(x=960, now=0.15)),
            MotionIntent(-300, 200, -100), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.RECOVER)
        self.assertEqual((decision.vx, decision.vy), (0, 0))
        self.assertGreater(decision.wz, 0)

    def test_goal_loss_stops_all_motion(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        decision = policy.update(
            frame(3, 0.15, ball=observation(now=0.15)),
            MotionIntent(300, 200, 100), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.ANCHOR_LOST)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_lost_goal_must_be_confirmed_again_before_motion(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        policy.update(frame(3, 0.15), enabled=True)

        first = policy.update(
            frame(4, 0.20, goal=observation(now=0.20)), enabled=True)
        second = policy.update(
            frame(5, 0.25, goal=observation(now=0.25)), enabled=True)
        third = policy.update(
            frame(6, 0.30, goal=observation(now=0.30)), enabled=True)

        self.assertEqual(first.state, GoalkeeperState.ANCHORING)
        self.assertEqual(second.state, GoalkeeperState.ANCHORING)
        self.assertEqual(third.state, GoalkeeperState.HOLD)

    def test_ball_loss_may_use_yaw_only_while_goal_remains_visible(self):
        policy = GoalkeeperPolicy()
        anchor(policy)
        policy.update(
            frame(3, 0.15, ball=observation(
                width=40, height=40, now=0.15),
                goal=observation(now=0.15)), enabled=True)
        decision = policy.update(
            frame(4, 0.20, goal=observation(now=0.20)),
            MotionIntent(200, 200, -80), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.BALL_LOST)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, -80))

    def test_stale_goal_cannot_preserve_relative_capability(self):
        policy = GoalkeeperPolicy(GoalkeeperConfig(max_observation_age=0.20))
        anchor(policy)
        stale = observation(now=0.0)
        decision = policy.update(
            frame(3, 0.50, goal=stale), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.ANCHOR_LOST)
        self.assertEqual(decision.capability, LocalizationCapability.INVALID)

    def test_invalid_frame_enters_fault(self):
        policy = GoalkeeperPolicy()
        invalid = PerceptionFrame(
            frame_id=0, captured_at=1.0, processed_at=0.0,
            frame_width=WIDTH, frame_height=HEIGHT)
        decision = policy.update(invalid, enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.FAULT)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_duplicate_frame_enters_fault(self):
        policy = GoalkeeperPolicy()
        policy.update(
            frame(0, 0.0, goal=observation(now=0.0)), enabled=True)
        decision = policy.update(
            frame(0, 0.05, goal=observation(now=0.05)), enabled=True)
        self.assertEqual(decision.state, GoalkeeperState.FAULT)
        self.assertEqual(decision.reason, "non-monotonic-frame")

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            GoalkeeperPolicy(GoalkeeperConfig(block_exit_area=1000.0))


if __name__ == "__main__":
    unittest.main()
