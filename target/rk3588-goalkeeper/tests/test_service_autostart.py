import contextlib
import io
import sys
from pathlib import Path
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from service_preflight import main as preflight_main  # noqa: E402
from service_preflight import (  # noqa: E402
    parse_args,
    wait_for_host,
    wait_for_path,
)


class ServiceAutostartTests(unittest.TestCase):
    def test_linux_entrypoints_use_lf_line_endings(self):
        for relative_path in (
                "autostart.sh", "motion_autostart.sh",
                "deploy/c5-goalkeeper.service",
                "deploy/c5-goalkeeper-motion.service"):
            with self.subTest(path=relative_path):
                source = (PROJECT / relative_path).read_bytes()
                self.assertNotIn(b"\r\n", source)

    def test_unit_is_network_independent_headless_dry_run(self):
        source = (
            PROJECT / "deploy" / "c5-goalkeeper.service"
        ).read_text(encoding="utf-8")
        self.assertIn("WantedBy=multi-user.target", source)
        self.assertIn("After=local-fs.target", source)
        self.assertIn("service_preflight.py", source)
        self.assertIn(
            "main.py --headless --mode goalkeeper-test "
            "--dry-run-duration 7200", source)
        self.assertNotIn("graphical.target", source)
        self.assertNotIn("network.target", source)
        self.assertNotIn("network-online.target", source)
        self.assertNotIn("DISPLAY=", source)
        self.assertNotIn("--execute", source)
        self.assertNotIn("--continuous", source)
        self.assertNotIn("pusher_cli", source)

    def test_installer_preserves_fixed_safe_exec_arguments(self):
        source = (PROJECT / "autostart.sh").read_text(encoding="utf-8")
        self.assertIn(
            "main.py --headless --mode goalkeeper-test "
            "--dry-run-duration 7200", source)
        self.assertIn("service_preflight.py --model", source)
        self.assertIn("--camera /dev/video0 --wait 30", source)
        self.assertNotIn("main.py --execute", source)
        self.assertNotIn("main.py --continuous", source)

    def test_motion_unit_is_separate_bounded_and_explicit(self):
        source = (
            PROJECT / "deploy" / "c5-goalkeeper-motion.service"
        ).read_text(encoding="utf-8")
        self.assertIn("Conflicts=c5-goalkeeper.service", source)
        self.assertIn(
            "ConditionPathExists=/etc/c5-goalkeeper-motion.enable", source)
        self.assertIn("--host auto --wait 30", source)
        self.assertIn(
            "--mode goalkeeper-motion --execute --duration 180 ", source)
        self.assertIn("--goalkeeper-motion-profile fast-lateral", source)
        self.assertIn("motion_cli.py stop", source)
        self.assertIn("Restart=no", source)
        self.assertNotIn("--goalkeeper-synthetic-goal", source)

    def test_motion_installer_defaults_to_disabled_without_gate(self):
        source = (PROJECT / "motion_autostart.sh").read_text(
            encoding="utf-8")
        self.assertIn("I_ACCEPT_AUTONOMOUS_MOTION", source)
        self.assertIn('systemctl disable "$SERVICE"', source)
        self.assertIn('rm -f "$GATE"', source)
        self.assertIn("enable-next-boot", source)
        self.assertIn("resolve_serial_port", source)
        self.assertIn('[ -e "$host" ]', source)
        self.assertNotIn("[ ! -e /dev/c5-host ]", source)
        self.assertNotIn("enable --now", source)

    def test_preflight_accepts_existing_model_and_camera(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.rknn"
            camera = Path(directory) / "video0"
            model.write_bytes(b"model")
            camera.touch()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = preflight_main([
                    "--model", str(model),
                    "--camera", str(camera),
                    "--wait", "0",
                ])
        self.assertEqual(result, 0)
        self.assertIn("PREFLIGHT OK", output.getvalue())

    def test_preflight_rejects_missing_model_without_camera_wait(self):
        sleeps = []
        self.assertFalse(wait_for_path(
            "definitely-missing-camera", 0.0,
            clock=lambda: 1.0, sleep=sleeps.append))
        self.assertEqual(sleeps, [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = preflight_main([
                "--model", "definitely-missing-model.rknn",
                "--camera", "definitely-missing-camera",
                "--wait", "30",
            ])
        self.assertEqual(result, 2)
        self.assertIn("model not found", output.getvalue())

    def test_preflight_rejects_missing_motion_host(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "model.rknn"
            camera = Path(directory) / "video0"
            model.write_bytes(b"model")
            camera.touch()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = preflight_main([
                    "--model", str(model),
                    "--camera", str(camera),
                    "--host", str(Path(directory) / "c5-host"),
                    "--wait", "0",
                ])
        self.assertEqual(result, 2)
        self.assertIn("HOST link not ready", output.getvalue())

    def test_auto_host_accepts_one_resolved_ch340(self):
        with tempfile.TemporaryDirectory() as directory:
            node = Path(directory) / "ttyUSB7"
            node.touch()
            resolved, error = wait_for_host(
                "auto", 0.0,
                resolver=lambda port: str(node))
        self.assertEqual(resolved, str(node))
        self.assertIsNone(error)

    def test_auto_host_rejects_missing_resolved_path(self):
        resolved, error = wait_for_host(
            "auto", 0.0,
            resolver=lambda port: "/definitely/missing/ttyUSB7")
        self.assertIsNone(resolved)
        self.assertIn("resolved path not found", error)

    def test_auto_host_reports_ambiguous_devices(self):
        def ambiguous(_port):
            raise RuntimeError("multiple CH340 devices found")

        resolved, error = wait_for_host(
            "auto", 0.0, resolver=ambiguous)
        self.assertIsNone(resolved)
        self.assertEqual(error, "multiple CH340 devices found")

    def test_preflight_wait_is_bounded(self):
        with self.assertRaises(SystemExit):
            parse_args([
                "--model", "model.rknn",
                "--wait", "121",
            ])


if __name__ == "__main__":
    unittest.main()
