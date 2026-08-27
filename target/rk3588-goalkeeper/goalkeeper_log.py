"""Replayable CSV telemetry for the dry-run goalkeeper policy."""

import csv
from pathlib import Path
import time


FIELDS = (
    "wall_time_s",
    "frame_id",
    "captured_at_s",
    "processed_at_s",
    "perception_age_s",
    "state",
    "capability",
    "reason",
    "ball_range",
    "ball_x_px",
    "ball_y_px",
    "ball_width_px",
    "ball_height_px",
    "ball_confidence",
    "ball_area_px2",
    "goal_x_px",
    "goal_y_px",
    "goal_width_px",
    "goal_height_px",
    "goal_confidence",
    "goal_error",
    "candidate_vx",
    "candidate_vy",
    "candidate_wz",
    "decision_vx",
    "decision_vy",
    "decision_wz",
    "pusher_intent",
    "valid_until_s",
)


class GoalkeeperCsvLogger:
    """Write one self-contained row for every goalkeeper policy update."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDS)
        self._writer.writeheader()
        self._file.flush()

    def write(self, frame, candidate, decision):
        ball = frame.ball
        goal = frame.opponent_goal
        self._writer.writerow({
            "wall_time_s": self._format(time.time()),
            "frame_id": frame.frame_id,
            "captured_at_s": self._format(frame.captured_at),
            "processed_at_s": self._format(frame.processed_at),
            "perception_age_s": self._format(
                frame.processed_at - frame.captured_at),
            "state": decision.state.value,
            "capability": decision.capability.value,
            "reason": decision.reason,
            "ball_range": decision.ball_range.value,
            "ball_x_px": self._value(ball, "x"),
            "ball_y_px": self._value(ball, "y"),
            "ball_width_px": self._value(ball, "width"),
            "ball_height_px": self._value(ball, "height"),
            "ball_confidence": self._value(ball, "confidence"),
            "ball_area_px2": "" if ball is None else self._format(ball.area),
            "goal_x_px": self._value(goal, "x"),
            "goal_y_px": self._value(goal, "y"),
            "goal_width_px": self._value(goal, "width"),
            "goal_height_px": self._value(goal, "height"),
            "goal_confidence": self._value(goal, "confidence"),
            "goal_error": self._format(decision.goal_error),
            "candidate_vx": candidate.vx,
            "candidate_vy": candidate.vy,
            "candidate_wz": candidate.wz,
            "decision_vx": decision.vx,
            "decision_vy": decision.vy,
            "decision_wz": decision.wz,
            "pusher_intent": decision.pusher.value,
            "valid_until_s": self._format(decision.valid_until),
        })
        self._file.flush()

    def close(self):
        if not self._file.closed:
            self._file.close()

    @staticmethod
    def _value(observation, name):
        if observation is None:
            return ""
        return GoalkeeperCsvLogger._format(getattr(observation, name))

    @staticmethod
    def _format(value):
        return f"{float(value):.6f}"
