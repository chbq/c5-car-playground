import csv
from collections import namedtuple
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from goalkeeper_log import FIELDS, GoalkeeperCsvLogger, make_default_log_path
from goalkeeper_policy import GoalkeeperState, PusherIntent
from goalkeeper_runtime import (
    GoalkeeperDryRunSession,
    GoalkeeperMotionSession,
    SyntheticGoalSpec,
)
from motion_link import MotionLinkNotArmedError


Info = namedtuple("Info", "x y width height conf ts")


def info(x, width, height, conf=0.9):
    return Info(x, 360, width, height, conf, 999.0)


def tick(session, frame_id, ball=None, goal=None):
    captured = 10.0 + frame_id * 0.02
    return session.tick(
        frame_id, captured, captured + 0.03, 1280, 720,
        ball_info=ball, goal_info=goal,
    )


def anchor(session):
    goal = info(640, 300, 250)
    for frame_id in range(3):
        result = tick(session, frame_id, goal=goal)
    return result


class FakeMotionLink:
    def __init__(self):
        self.arm_count = 0
        self.twists = []
        self.stop_count = 0

    def arm(self):
        self.arm_count += 1

    def set_twist(self, vx, vy, wz):
        self.twists.append((vx, vy, wz))

    def safe_stop(self):
        self.stop_count += 1


class OneShotDisarmMotionLink(FakeMotionLink):
    def __init__(self):
        super().__init__()
        self.reject_next_twist = True

    def set_twist(self, vx, vy, wz):
        if self.reject_next_twist:
            self.reject_next_twist = False
            raise MotionLinkNotArmedError("test timeout")
        super().set_twist(vx, vy, wz)


class GoalkeeperRuntimeTests(unittest.TestCase):
    def test_synthetic_goal_requires_an_in_frame_box(self):
        with self.assertRaises(ValueError):
            SyntheticGoalSpec(0.1, 0.5, 0.5, 0.5).validate()

    def test_synthetic_goal_anchors_without_detector_goal(self):
        session = GoalkeeperDryRunSession(
            synthetic_goal=SyntheticGoalSpec(0.5, 0.4, 0.5, 0.5))
        for frame_id in range(3):
            captured = 10.0 + frame_id * 0.02
            frame, _, decision = session.tick(
                frame_id, captured, captured + 1.0, 1280, 720,
                goal_info=None)
        self.assertEqual(frame.opponent_goal.x, 640.0)
        self.assertEqual(frame.opponent_goal.width, 640.0)
        self.assertAlmostEqual(frame.opponent_goal.captured_at, 11.04)
        self.assertEqual(decision.state, GoalkeeperState.HOLD)

    def test_default_log_path_has_offline_collision_token(self):
        path = make_default_log_path(
            directory="logs", wall_time=0, run_id="deadbeef")
        self.assertEqual(path.parent, Path("logs"))
        self.assertTrue(path.name.endswith("-deadbeef.csv"))

    def test_session_requires_goal_anchor_before_ball_motion(self):
        session = GoalkeeperDryRunSession()
        _, candidate, decision = tick(
            session, 0, ball=info(300, 40, 40), goal=None)
        self.assertGreater(candidate.vx, 0)
        self.assertLess(candidate.wz, 0)
        self.assertEqual(decision.state, GoalkeeperState.ANCHORING)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_session_preserves_signed_phase5c_candidate_when_intercepting(self):
        session = GoalkeeperDryRunSession()
        anchor(session)
        _, candidate, decision = tick(
            session, 3, ball=info(300, 45, 45), goal=info(640, 300, 250))
        self.assertGreater(candidate.vx, 0)
        self.assertLess(candidate.wz, 0)
        self.assertEqual(decision.state, GoalkeeperState.INTERCEPT)
        self.assertGreater(decision.vx, 0)
        self.assertLess(decision.wz, 0)

    def test_close_ball_only_requests_abstract_pusher_intent(self):
        session = GoalkeeperDryRunSession()
        anchor(session)
        _, _, decision = tick(
            session, 3, ball=info(640, 100, 90), goal=info(640, 300, 250))
        self.assertEqual(decision.state, GoalkeeperState.CLOSE_BLOCK)
        self.assertEqual(decision.pusher, PusherIntent.CYCLE)
        self.assertEqual((decision.vx, decision.vy, decision.wz), (0, 0, 0))

    def test_csv_contains_replay_inputs_candidates_and_policy_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "goalkeeper.csv"
            logger = GoalkeeperCsvLogger(path)
            session = GoalkeeperDryRunSession(logger=logger)
            tick(
                session, 0, ball=info(300, 40, 40),
                goal=info(640, 300, 250))
            logger.close()

            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(tuple(rows[0]), FIELDS)
        self.assertEqual(rows[0]["frame_id"], "0")
        self.assertEqual(rows[0]["ball_x_px"], "300.000000")
        self.assertEqual(rows[0]["goal_x_px"], "640.000000")
        self.assertGreater(int(rows[0]["candidate_vx"]), 0)
        self.assertEqual(rows[0]["decision_vx"], "0")

    def test_motion_requires_three_policy_approved_commands_before_arm(self):
        link = FakeMotionLink()
        session = GoalkeeperMotionSession(link, acquire_cycles=3)
        anchor(session)
        for frame_id in (3, 4):
            tick(session, frame_id, ball=info(300, 45, 45),
                 goal=info(640, 300, 250))
        self.assertEqual(link.arm_count, 0)
        tick(session, 5, ball=info(300, 45, 45),
             goal=info(640, 300, 250))
        self.assertEqual(link.arm_count, 1)
        self.assertGreater(link.twists[-1][0], 0)
        self.assertLess(link.twists[-1][2], 0)

    def test_motion_goal_loss_stops_and_disarms_immediately(self):
        link = FakeMotionLink()
        session = GoalkeeperMotionSession(link, acquire_cycles=1)
        anchor(session)
        tick(session, 3, ball=info(300, 45, 45),
             goal=info(640, 300, 250))
        self.assertTrue(session.armed)
        tick(session, 4, ball=info(300, 45, 45), goal=None)
        self.assertFalse(session.armed)
        self.assertEqual(link.stop_count, 1)
        self.assertEqual(
            (session.last_sent_vx, session.last_sent_vy,
             session.last_sent_wz), (0, 0, 0))

    def test_motion_reacquires_after_stm32_timeout_disarm(self):
        link = OneShotDisarmMotionLink()
        session = GoalkeeperMotionSession(link, acquire_cycles=2)
        anchor(session)
        tick(session, 3, ball=None, goal=info(800, 300, 250))
        tick(session, 4, ball=None, goal=info(800, 300, 250))
        self.assertFalse(session.finished)
        self.assertFalse(session.armed)
        self.assertEqual(link.arm_count, 1)
        self.assertEqual(link.stop_count, 1)

        tick(session, 5, ball=None, goal=info(800, 300, 250))
        self.assertEqual(link.arm_count, 1)
        tick(session, 6, ball=None, goal=info(800, 300, 250))
        self.assertTrue(session.armed)
        self.assertEqual(link.arm_count, 2)
        self.assertTrue(link.twists)

    def test_close_ball_stops_chassis_without_driving_pusher(self):
        link = FakeMotionLink()
        session = GoalkeeperMotionSession(link, acquire_cycles=1)
        anchor(session)
        tick(session, 3, ball=info(300, 45, 45),
             goal=info(640, 300, 250))
        _, _, decision = tick(
            session, 4, ball=info(640, 100, 90),
            goal=info(640, 300, 250))
        self.assertEqual(decision.pusher, PusherIntent.CYCLE)
        self.assertFalse(session.armed)
        self.assertEqual(link.stop_count, 1)
