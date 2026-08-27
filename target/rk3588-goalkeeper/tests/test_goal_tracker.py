import sys
from pathlib import Path
from types import ModuleType
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
# 跟踪器测试不涉及图像操作；让宿主测试不依赖香橙派的 OpenCV 运行时。
sys.modules.setdefault("cv2", ModuleType("cv2"))

from goal_tracker import GoalTracker  # noqa: E402


class GoalTrackerTests(unittest.TestCase):
    def test_preserves_box_and_update_result(self):
        tracker = GoalTracker()
        result = tracker.update(
            boxes=[[10, 20, 50, 80], [100, 100, 140, 180]],
            classes=[1, 1],
            scores=[0.7, 0.9],
        )
        self.assertEqual(result, (120, 140, 0.9))
        info = tracker.get(max_age=None)
        self.assertEqual((info.x, info.y), (120, 140))
        self.assertEqual((info.width, info.height), (40, 80))
        self.assertEqual(info.conf, 0.9)
        self.assertEqual(
            tracker.get_box(max_age=None), (100.0, 100.0, 140.0, 180.0))

    def test_ignores_football_class(self):
        tracker = GoalTracker()
        result = tracker.update(
            boxes=[[10, 20, 50, 80], [100, 100, 140, 180]],
            classes=[0, 0],  # 都是 football，不是 goal
            scores=[0.7, 0.9],
        )
        self.assertIsNone(result)
        self.assertIsNone(tracker.get(max_age=None))
        self.assertIsNone(tracker.get_box(max_age=None))

    def test_empty_frame_clears_cached_detection(self):
        tracker = GoalTracker()
        tracker.update([[10, 20, 50, 80]], [1], [0.9])
        self.assertIsNone(tracker.update(None, [], []))
        self.assertIsNone(tracker.get(max_age=None))
        self.assertIsNone(tracker.get_box(max_age=None))

    def test_caches_and_exposes_goal_geometry(self):
        tracker = GoalTracker()
        tracker.update([[10, 20, 50, 80]], [1], [0.9])
        corners = {
            "TL": (10, 20), "TR": (50, 20),
            "BL": None, "BR": None,
            "top_width": 40.0, "source": "posts",
        }
        tracker.update_geometry(corners)
        self.assertEqual(tracker.get_top_width(max_age=None), 40.0)
        self.assertEqual(
            tracker.get_corners(max_age=None)["top_width"], 40.0)
        tracker.update_geometry(None)
        self.assertIsNone(tracker.get_top_width(max_age=None))
        self.assertIsNone(tracker.get_corners(max_age=None))

    def test_box_loss_clears_geometry(self):
        tracker = GoalTracker()
        tracker.update([[10, 20, 50, 80]], [1], [0.9])
        tracker.update_geometry(
            {"TL": (1, 1), "TR": (2, 2), "top_width": 1.0, "source": "posts"})
        self.assertIsNotNone(tracker.get_top_width(max_age=None))
        tracker.update(None, [], [])  # 球门丢失
        self.assertIsNone(tracker.get_top_width(max_age=None))
        self.assertIsNone(tracker.get_corners(max_age=None))

    def test_compute_geometry_uses_pc_process_goal(self):
        import goal_tracker as gt
        tracker = GoalTracker()
        tracker.update([[10, 20, 50, 80]], [1], [0.9])
        fake = {
            "TL": (10, 20), "TR": (50, 20),
            "BL": None, "BR": None,
            "top_width": 40.0, "source": "hough",
        }
        calls = []
        original = gt.process_goal

        def fake_process_goal(frame, box, **kwargs):
            calls.append((frame, box, kwargs))
            return fake

        gt.process_goal = fake_process_goal
        try:
            result = tracker.compute_geometry("FRAME")
        finally:
            gt.process_goal = original

        self.assertEqual(result, fake)
        self.assertEqual(len(calls), 1)
        frame_arg, box_arg, kwargs = calls[0]
        self.assertEqual(frame_arg, "FRAME")
        self.assertEqual(box_arg, (10.0, 20.0, 50.0, 80.0))
        self.assertEqual(kwargs["margin_side"], 0.05)
        self.assertEqual(kwargs["margin_top"], 0.15)
        self.assertEqual(kwargs["roi_bottom_frac"], 0.2)
        self.assertEqual(kwargs["method"], "fused")
        self.assertEqual(kwargs["corner_method"], "auto")
        self.assertEqual(tracker.get_top_width(max_age=None), 40.0)

    def test_compute_geometry_without_box_returns_none(self):
        tracker = GoalTracker()
        tracker.update_geometry(
            {"TL": (1, 1), "TR": (2, 2), "top_width": 1.0, "source": "posts"})
        self.assertIsNone(tracker.compute_geometry("FRAME"))
        self.assertIsNone(tracker.get_top_width(max_age=None))


if __name__ == "__main__":
    unittest.main()
