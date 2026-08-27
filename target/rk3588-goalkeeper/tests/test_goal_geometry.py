import sys
from pathlib import Path
from types import ModuleType
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
# goal_geometry 模块级只依赖 numpy（WHITE_LOWER/UPPER 用 np.array）；
# 这里只测不调用 cv2 的纯函数（expand_roi/_longest_run/_line_intersection），
# stub 掉 cv2 使宿主测试不依赖香橙派 OpenCV 运行时。
sys.modules.setdefault("cv2", ModuleType("cv2"))

from goal_geometry import expand_roi, _longest_run, _line_intersection  # noqa: E402


class GoalGeometryPureTests(unittest.TestCase):
    def test_expand_roi_scales_and_clamps(self):
        self.assertEqual(
            expand_roi([100, 100, 200, 200], (720, 1280)),
            (80, 80, 220, 150),
        )

    def test_expand_roi_clamps_to_image_bounds(self):
        self.assertEqual(
            expand_roi([10, 10, 20, 20], (720, 1280)),
            (8, 8, 22, 15),
        )

    def test_expand_roi_clamps_fully_outside_box(self):
        self.assertEqual(
            expand_roi([-100, 10, -50, 20], (720, 1280)),
            (0, 8, 0, 15),
        )

    def test_longest_run(self):
        self.assertEqual(
            _longest_run([False, True, True, True, False, True]),
            (1, 3),
        )
        self.assertIsNone(_longest_run([False, False]))
        self.assertEqual(_longest_run([True, True]), (0, 1))

    def test_line_intersection(self):
        self.assertEqual(
            _line_intersection((0, 0), (10, 0), (5, -10), (5, 10)),
            (5, 0),
        )
        self.assertIsNone(
            _line_intersection((0, 0), (10, 0), (0, 5), (10, 5)))


if __name__ == "__main__":
    unittest.main()
