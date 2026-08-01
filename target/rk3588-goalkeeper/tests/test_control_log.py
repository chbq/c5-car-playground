import csv
import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from control_log import ControlCsvLogger, FIELDS  # noqa: E402


class ControlCsvLoggerTests(unittest.TestCase):
    def test_writes_detection_commands_session_and_imu(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.csv"
            logger = ControlCsvLogger(path, "ball-follow-test")
            observation = SimpleNamespace(
                x=900, y=320, width=80, height=120)
            decision = SimpleNamespace(
                state=SimpleNamespace(value="TRACKING"),
                confidence=0.9,
                error=0.4,
                filtered_error=0.35,
                error_rate=1.5,
                predicted_error=0.575,
                zone=SimpleNamespace(value="EDGE"),
                target_age=0.0,
                lost_frames=0,
                predicted_only=False,
                box_ratio=1 / 6,
                distance_error=0.18,
                vx=-400,
                vy=600,
                wz=80,
            )
            session = SimpleNamespace(
                last_sent_vx=-400,
                last_sent_vy=600,
                last_sent_wz=80,
                armed=True,
                paused=False,
            )
            logger.write(
                12.5, observation, decision, session,
                pitch=1.0, roll=2.0, yaw=3.0)
            logger.close()

            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(tuple(rows[0]), FIELDS)
            self.assertEqual(rows[0]["target_vx"], "-400")
            self.assertEqual(rows[0]["sent_vy"], "600")
            self.assertEqual(rows[0]["yaw_deg"], "3.000000")
            self.assertEqual(rows[0]["armed"], "1")
            self.assertEqual(rows[0]["fov_zone"], "EDGE")
            self.assertEqual(rows[0]["predicted_x_error"], "0.575000")
            self.assertEqual(rows[0]["predicted_only"], "0")

    def test_dry_run_keeps_sent_fields_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dry.csv"
            logger = ControlCsvLogger(path, "ball-follow-test")
            decision = SimpleNamespace(
                state=SimpleNamespace(value="NO_TARGET"),
                confidence=None,
                error=0.0,
                box_ratio=0.0,
                distance_error=0.0,
                vx=0,
                vy=0,
                wz=0,
            )
            session = SimpleNamespace(
                last_sent_vx=None,
                last_sent_vy=None,
                last_sent_wz=None,
                armed=False,
                paused=False,
            )
            logger.write(1.0, None, decision, session)
            logger.close()

            with path.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["sent_vx"], "")
            self.assertEqual(row["x_px"], "")
            self.assertEqual(row["armed"], "0")


if __name__ == "__main__":
    unittest.main()
