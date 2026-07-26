import ast
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]


def read_constants(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    constants = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            try:
                constants[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
        elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
            for item, value in zip(target.elts, node.value.elts):
                if isinstance(item, ast.Name):
                    try:
                        constants[item.id] = ast.literal_eval(value)
                    except (ValueError, TypeError):
                        pass
    return constants


class RuntimeConfigTests(unittest.TestCase):
    def test_latest_visual_model_configuration_is_preserved(self):
        constants = read_constants(PROJECT / "main.py")
        self.assertEqual(constants["MODEL_PATH"],
                         "./rknnModel/model_26.7.25_i8.rknn")
        self.assertEqual(constants["TPEs"], 6)

    def test_motion_link_does_not_regress_to_debug_uart(self):
        main_source = (PROJECT / "main.py").read_text(encoding="utf-8")
        self.assertIn("from motion_link import MotionLink", main_source)
        self.assertNotIn("/dev/ttyS0", main_source)
        self.assertNotIn("send_football_x", main_source)

    def test_latest_detection_thresholds_are_preserved(self):
        constants = read_constants(PROJECT / "func.py")
        self.assertEqual(constants["OBJ_THRESH"], 0.25)
        self.assertEqual(constants["NMS_THRESH"], 0.2)
        self.assertEqual(constants["IMG_SIZE"], 640)


if __name__ == "__main__":
    unittest.main()
