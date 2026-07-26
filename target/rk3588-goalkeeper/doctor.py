"""Read-only Orange Pi environment audit for the goalkeeper project."""

import getpass
import grp
import importlib.util
import os
from pathlib import Path
import platform
import sys

SERIAL_PORT = Path("/dev/ttyS7")
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
    serial_nodes = sorted(Path("/dev").glob("ttyS*"))
    print(f"serial nodes: {len(serial_nodes)}")
    for node in serial_nodes[:16]:
        print(f"  {node}")
    print(f"serial: {SERIAL_PORT} {mark(SERIAL_PORT.exists())}")
    if SERIAL_PORT.exists():
        print(f"serial read/write: {os.access(SERIAL_PORT, os.R_OK | os.W_OK)}")
    for name in MODULES:
        print(f"module {name}: {mark(importlib.util.find_spec(name) is not None)}")
    models = sorted(Path(__file__).parent.joinpath("rknnModel").glob("*.rknn"))
    print(f"models: {len(models)}")
    for model in models[:8]:
        print(f"  {model.name} ({model.stat().st_size} bytes)")
    print("audit is read-only; UART overlay, groups and packages are not changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
