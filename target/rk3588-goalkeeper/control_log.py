"""Full-rate CSV telemetry for bounded ball-control sessions."""

import csv
from pathlib import Path
import time


FIELDS = (
    "wall_time_s",
    "monotonic_s",
    "mode",
    "state",
    "x_px",
    "y_px",
    "box_width_px",
    "box_height_px",
    "confidence",
    "x_error",
    "filtered_x_error",
    "x_error_rate_s",
    "predicted_x_error",
    "fov_zone",
    "target_age_s",
    "lost_frames",
    "predicted_only",
    "box_ratio",
    "distance_error",
    "target_vx",
    "target_vy",
    "target_wz",
    "sent_vx",
    "sent_vy",
    "sent_wz",
    "armed",
    "paused",
    "pitch_deg",
    "roll_deg",
    "yaw_deg",
)


class ControlCsvLogger:
    """Write and flush one diagnostic row per controller tick."""

    def __init__(self, path, mode):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDS)
        self._writer.writeheader()
        self._file.flush()
        self.mode = mode

    def write(self, now, observation, decision, session,
              pitch=None, roll=None, yaw=None):
        self._writer.writerow({
            "wall_time_s": f"{time.time():.6f}",
            "monotonic_s": f"{now:.6f}",
            "mode": self.mode,
            "state": decision.state.value,
            "x_px": self._value(observation, "x"),
            "y_px": self._value(observation, "y"),
            "box_width_px": self._value(observation, "width"),
            "box_height_px": self._value(observation, "height"),
            "confidence": self._format(decision.confidence),
            "x_error": self._format(decision.error),
            "filtered_x_error": self._format(
                getattr(decision, "filtered_error", None)),
            "x_error_rate_s": self._format(
                getattr(decision, "error_rate", None)),
            "predicted_x_error": self._format(
                getattr(decision, "predicted_error", None)),
            "fov_zone": self._enum_value(
                getattr(decision, "zone", None)),
            "target_age_s": self._format(
                getattr(decision, "target_age", None)),
            "lost_frames": getattr(decision, "lost_frames", ""),
            "predicted_only": int(
                bool(getattr(decision, "predicted_only", False))),
            "box_ratio": self._format(decision.box_ratio),
            "distance_error": self._format(decision.distance_error),
            "target_vx": decision.vx,
            "target_vy": decision.vy,
            "target_wz": decision.wz,
            "sent_vx": self._sent(session, "last_sent_vx"),
            "sent_vy": self._sent(session, "last_sent_vy"),
            "sent_wz": self._sent(session, "last_sent_wz"),
            "armed": int(session.armed),
            "paused": int(session.paused),
            "pitch_deg": self._format(pitch),
            "roll_deg": self._format(roll),
            "yaw_deg": self._format(yaw),
        })
        self._file.flush()

    def close(self):
        if not self._file.closed:
            self._file.close()

    @staticmethod
    def _value(obj, name):
        if obj is None:
            return ""
        value = getattr(obj, name, None)
        return "" if value is None else value

    @staticmethod
    def _format(value):
        return "" if value is None else f"{float(value):.6f}"

    @staticmethod
    def _enum_value(value):
        return "" if value is None else getattr(value, "value", str(value))

    @staticmethod
    def _sent(session, name):
        value = getattr(session, name, None)
        return "" if value is None else value
