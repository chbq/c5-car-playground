import contextlib
import io
import sys
from pathlib import Path
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from pusher_cli import main, parse_args  # noqa: E402


class PusherCliTests(unittest.TestCase):
    def test_default_is_read_only_stable_alias_query(self):
        args = parse_args([])
        self.assertIsNone(args.action)
        self.assertEqual(args.port, "/dev/c5-pusher")

    def test_cycle_requires_all_hardware_inputs(self):
        with self.assertRaises(SystemExit):
            parse_args(["cycle", "--stroke-pulses", "100"])

    def test_missing_execute_does_not_construct_link(self):
        constructed = []

        def factory(*args, **kwargs):
            constructed.append((args, kwargs))
            raise AssertionError("link must not be opened")

        argv = [
            "cycle", "--stroke-pulses", "100", "--speed-rpm", "50",
            "--acceleration", "10", "--outward-direction", "cw",
            "--idle-behavior", "hold",
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            result = main(argv, link_factory=factory)
        self.assertEqual(result, 1)
        self.assertEqual(constructed, [])


if __name__ == "__main__":
    unittest.main()
