import sys
from pathlib import Path
from types import ModuleType
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
# The tracker test does not exercise image operations; keep host tests
# independent of the Orange Pi OpenCV runtime.
sys.modules.setdefault("cv2", ModuleType("cv2"))

from football_tracker import FootballTracker  # noqa: E402


class FootballTrackerTests(unittest.TestCase):
    def test_preserves_box_size_without_breaking_update_result(self):
        tracker = FootballTracker()
        result = tracker.update(
            boxes=[[10, 20, 50, 80], [100, 100, 140, 180]],
            classes=[0, 0],
            scores=[0.7, 0.9],
        )
        self.assertEqual(result, (120, 140, 0.9))
        info = tracker.get(max_age=None)
        self.assertEqual((info.x, info.y), (120, 140))
        self.assertEqual((info.width, info.height), (40, 80))
        self.assertEqual(info.conf, 0.9)

    def test_empty_frame_clears_cached_detection(self):
        tracker = FootballTracker()
        tracker.update([[10, 20, 50, 80]], [0], [0.9])
        self.assertIsNone(tracker.update(None, [], []))
        self.assertIsNone(tracker.get(max_age=None))


if __name__ == "__main__":
    unittest.main()
