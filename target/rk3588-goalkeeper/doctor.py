"""Read-only Orange Pi environment audit for the goalkeeper project."""

import getpass
import grp
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys

from serial_transport import find_ch340_by_id_paths, resolve_serial_port

MODULES = ("serial", "smbus2", "cv2", "numpy", "rknnlite")
BOOT_CONFIGS = (Path("/boot/orangepiEnv.txt"), Path("/boot/armbianEnv.txt"))


def mark(ok):
    return "OK" if ok else "MISSING"


def read_board_model():
    path = Path("/proc/device-tree/model")
    if not path.is_file():
        return "UNKNOWN"
    return path.read_bytes().rstrip(b"\0").decode("utf-8", errors="replace")


def read_boot_setting(name):
    for path in BOOT_CONFIGS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                return value.strip()
    return "UNKNOWN"


def service_is_active(name):
    result = subprocess.run(
        ("systemctl", "is-active", "--quiet", name),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def service_enablement(name):
    try:
        result = subprocess.run(
            ("systemctl", "is-enabled", name),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def main():
    print(f"system: {platform.platform()}")
    print(f"machine: {platform.machine()}")
    print(f"board: {read_board_model()}")
    print(f"device tree: {read_boot_setting('fdtfile')}")
    print(f"overlays: {read_boot_setting('overlays')}")
    print(f"user: {getpass.getuser()}")
    print(f"python: {sys.version.split()[0]} ({sys.executable})")
    groups = sorted({grp.getgrgid(group_id).gr_name for group_id in os.getgroups()})
    print(f"groups: {','.join(groups)}")
    serial_nodes = sorted(Path("/dev").glob("ttyUSB*"))
    print("host transport: USB CH340 -> STM32 USART1")
    print(f"ttyUSB nodes: {len(serial_nodes)}")
    for node in serial_nodes[:16]:
        print(f"  {node}")
    by_id_paths = find_ch340_by_id_paths()
    print(f"CH340 by-id links: {len(by_id_paths)}")
    for path in by_id_paths[:8]:
        print(f"  {path}")
    try:
        serial_port = Path(resolve_serial_port())
    except RuntimeError as exc:
        print(f"serial: MISSING ({exc})")
    else:
        print(f"serial: {serial_port} {mark(serial_port.exists())}")
        print(f"serial read/write: {os.access(serial_port, os.R_OK | os.W_OK)}")
    brltty_active = service_is_active("brltty-udev.service")
    brltty_enablement = service_enablement("brltty-udev.service")
    if brltty_active:
        brltty_status = f"{brltty_enablement}/ACTIVE (can claim CH340)"
    elif brltty_enablement == "masked":
        brltty_status = "masked/inactive"
    else:
        brltty_status = (
            f"{brltty_enablement}/inactive (may claim CH340 after reboot)")
    print(f"brltty-udev: {brltty_status}")
    for name in MODULES:
        print(f"module {name}: {mark(importlib.util.find_spec(name) is not None)}")
    models = sorted(Path(__file__).parent.joinpath("rknnModel").glob("*.rknn"))
    print(f"models: {len(models)}")
    for model in models[:8]:
        print(f"  {model.name} ({model.stat().st_size} bytes)")
    print("audit is read-only; USB, groups and packages are not changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
