import sys
from pathlib import Path
import tempfile
import types
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from serial_transport import (  # noqa: E402
    find_ch340_by_id_paths,
    open_ch340_serial,
    resolve_serial_port,
)


class FakeClosedSerial:
    def __init__(self):
        self.port = None
        self.baudrate = None
        self.timeout = None
        self.write_timeout = None
        self.dtr = True
        self.rts = True
        self.exclusive = False
        self.opened_with = None

    def open(self):
        self.opened_with = (self.dtr, self.rts)


class SerialTransportTests(unittest.TestCase):
    def test_explicit_and_environment_ports_take_precedence(self):
        self.assertEqual(resolve_serial_port("/dev/custom"), "/dev/custom")
        self.assertEqual(
            resolve_serial_port(
                environ={"C5_HOST_PORT": "/dev/from-env"},
                stable_alias="missing",
            ),
            "/dev/from-env",
        )

    def test_single_ch340_by_id_path_is_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usb-1a86_USB_Serial-if00-port0"
            path.touch()
            self.assertEqual(find_ch340_by_id_paths(directory), [str(path)])
            self.assertEqual(
                resolve_serial_port(
                    environ={}, by_id_dir=directory,
                    ttyusb_glob=str(Path(directory) / "ttyUSB*"),
                    stable_alias=str(Path(directory) / "missing"),
                ),
                str(path),
            )

    def test_ambiguous_ch340_devices_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "usb-1a86_USB_Serial-A").touch()
            (Path(directory) / "usb-WCH_CH340-B").touch()
            with self.assertRaisesRegex(RuntimeError, "multiple CH340"):
                resolve_serial_port(
                    environ={}, by_id_dir=directory,
                    ttyusb_glob=str(Path(directory) / "ttyUSB*"),
                    stable_alias=str(Path(directory) / "missing"),
                )

    def test_single_ttyusb_is_bringup_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            node = Path(directory) / "ttyUSB0"
            node.touch()
            self.assertEqual(
                resolve_serial_port(
                    environ={}, by_id_dir=str(Path(directory) / "by-id"),
                    ttyusb_glob=str(Path(directory) / "ttyUSB*"),
                    stable_alias=str(Path(directory) / "missing"),
                ),
                str(node),
            )

    def test_control_lines_are_deasserted_before_open(self):
        connection = FakeClosedSerial()
        module = types.SimpleNamespace(Serial=lambda: connection)
        opened = open_ch340_serial("/dev/test", 115200, module)
        self.assertIs(opened, connection)
        self.assertEqual(connection.opened_with, (False, False))
        self.assertEqual(connection.port, "/dev/test")
        self.assertEqual(connection.baudrate, 115200)
        self.assertTrue(connection.exclusive)


if __name__ == "__main__":
    unittest.main()
