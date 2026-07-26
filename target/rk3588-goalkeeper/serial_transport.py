"""C5 USB serial discovery and conservative CH340 open helpers."""

import glob
import os
from pathlib import Path


AUTO_PORT = "auto"
_CH340_NAME_MARKERS = ("1a86", "ch340", "wch", "usb_serial")


def find_ch340_by_id_paths(by_id_dir="/dev/serial/by-id"):
    """Return stable Linux by-id paths whose names identify a CH340 device."""
    root = Path(by_id_dir)
    if not root.is_dir():
        return []
    paths = []
    for path in root.iterdir():
        name = path.name.lower()
        if any(marker in name for marker in _CH340_NAME_MARKERS):
            paths.append(str(path))
    return sorted(paths)


def resolve_serial_port(port=AUTO_PORT, environ=None, by_id_dir=None,
                        ttyusb_glob="/dev/ttyUSB*",
                        stable_alias="/dev/c5-host"):
    """Resolve AUTO_PORT to one unambiguous CH340 device path.

    C5_HOST_PORT and /dev/c5-host take precedence. A single CH340 by-id link is
    preferred. A lone ttyUSB node is accepted only as a bring-up fallback.
    """
    if port != AUTO_PORT:
        return port

    env = os.environ if environ is None else environ
    configured = env.get("C5_HOST_PORT")
    if configured:
        return configured

    alias_path = Path(stable_alias)
    if alias_path.exists():
        return str(alias_path)

    candidates = find_ch340_by_id_paths(
        "/dev/serial/by-id" if by_id_dir is None else by_id_dir
    )
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise RuntimeError(
            "multiple CH340 devices found; set C5_HOST_PORT or pass --port"
        )

    fallback = sorted(glob.glob(ttyusb_glob))
    if len(fallback) == 1:
        return fallback[0]
    if len(fallback) > 1:
        raise RuntimeError(
            "multiple ttyUSB devices found; set C5_HOST_PORT or pass --port"
        )
    raise RuntimeError(
        "CH340 not found; connect the C5 USB cable or pass an explicit port"
    )


def open_ch340_serial(port, baudrate, serial_module):
    """Open pyserial with DTR/RTS deasserted before the port is opened."""
    connection = serial_module.Serial()
    connection.port = port
    connection.baudrate = baudrate
    connection.timeout = 0.02
    connection.write_timeout = 0.1
    connection.dtr = False
    connection.rts = False
    connection.exclusive = True
    connection.open()
    return connection
