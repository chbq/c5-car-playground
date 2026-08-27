import csv
from collections import namedtuple
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from goalkeeper_log import FIELDS, GoalkeeperCsvLogger
from goalkeeper_policy import GoalkeeperState, PusherIntent
from goalkeeper_runtime import GoalkeeperDryRunSession


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


class GoalkeeperRuntimeTests(unittest.TestCase):
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
