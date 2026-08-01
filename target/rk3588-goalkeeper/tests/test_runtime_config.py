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
        constants = read_constants(PROJECT / "main.py")
        main_source = (PROJECT / "main.py").read_text(encoding="utf-8")
        self.assertEqual(constants["SERIAL_PORT"], "auto")
        self.assertIn("from motion_link import MotionLink", main_source)
        self.assertNotIn("/dev/ttyS0", main_source)
        self.assertNotIn("/dev/ttyS7", main_source)
        self.assertNotIn("send_football_x", main_source)

    def test_latest_detection_thresholds_are_preserved(self):
        constants = read_constants(PROJECT / "func.py")
        self.assertEqual(constants["OBJ_THRESH"], 0.25)
        self.assertEqual(constants["NMS_THRESH"], 0.2)
        self.assertEqual(constants["IMG_SIZE"], 640)

    def test_ground_profiles_are_repeatable_and_bounded(self):
        profiles = read_constants(PROJECT / "main.py")["BALL_PROFILES"]
        self.assertEqual(
            profiles["ground-check"],
            {
                "duration": 15.0,
                "min_wz": 60,
                "max_wz": 120,
                "kp": 150.0,
                "deadband": 0.12,
                "min_confidence": 0.35,
                "lost_timeout": 1.5,
                "hold_arm_until_duration": True,
            },
        )
        self.assertEqual(
            profiles["ground-demo"],
            {
                "duration": 30.0,
                "min_wz": 70,
                "max_wz": 160,
                "kp": 200.0,
                "deadband": 0.12,
                "min_confidence": 0.35,
                "lost_timeout": 1.5,
                "hold_arm_until_duration": True,
            },
        )

    def test_ball_strafe_defaults_are_aggressive_and_bounded(self):
        defaults = read_constants(PROJECT / "main.py")["BALL_STRAFE_DEFAULTS"]
        self.assertEqual(
            defaults,
            {
                "duration": 30.0,
                "min_vy": 250,
                "max_vy": 800,
                "lateral_kp": 1000.0,
                "lateral_deadband": 0.10,
                "max_vy_step": 120,
                "lateral_sign": -1,
                "min_confidence": 0.35,
                "lost_timeout": 1.5,
                "hold_arm_until_duration": True,
            },
        )

    def test_ball_follow_defaults_define_camera_axes(self):
        defaults = read_constants(PROJECT / "main.py")["BALL_FOLLOW_DEFAULTS"]
        self.assertEqual(defaults["max_vx"], 800)
        self.assertEqual(defaults["max_vy"], 600)
        self.assertEqual(defaults["max_wz"], 180)
        self.assertEqual(defaults["vx_kp"], 1000.0)
        self.assertEqual(defaults["vx_sign"], -1)
        self.assertEqual(defaults["distance_kp"], 4000.0)
        self.assertEqual(defaults["distance_deadband"], 0.05)
        self.assertEqual(defaults["target_box_ratio"], 0.35)
        self.assertEqual(defaults["vy_sign"], 1)
        self.assertEqual(defaults["yaw_sign"], 1)
        self.assertTrue(defaults["hold_arm_until_duration"])

    def test_ball_fov_defaults_prioritize_bounded_yaw(self):
        defaults = read_constants(PROJECT / "main.py")["BALL_FOV_DEFAULTS"]
        self.assertEqual(defaults["max_wz"], 260)
        self.assertEqual(defaults["kp"], 320.0)
        self.assertEqual(defaults["fov_edge_enter"], 0.55)
        self.assertEqual(defaults["fov_edge_exit"], 0.30)
        self.assertEqual(defaults["fov_prediction_horizon"], 0.15)
        self.assertEqual(defaults["fov_predict_hold"], 0.15)
        self.assertEqual(defaults["fov_translation_scale"], 0.25)
        self.assertLessEqual(defaults["fov_predict_hold"], 0.2)
        self.assertTrue(defaults["hold_arm_until_duration"])


if __name__ == "__main__":
    unittest.main()
