"""Read-only boot preflight for goalkeeper camera and optional HOST link."""

import argparse
from pathlib import Path
import time

from serial_transport import AUTO_PORT, resolve_serial_port


MAX_WAIT_SECONDS = 120.0


def wait_for_path(path, wait_seconds, poll_seconds=0.25,
                  clock=time.monotonic, sleep=time.sleep):
    """Wait for one boot-time device path without opening the device."""
    path = Path(path)
    deadline = clock() + wait_seconds
    while True:
        if path.exists():
            return True
        remaining = deadline - clock()
        if remaining <= 0:
            return False
        sleep(min(poll_seconds, remaining))


def wait_for_host(host, wait_seconds, poll_seconds=0.25,
                  resolver=resolve_serial_port,
                  clock=time.monotonic, sleep=time.sleep):
    """Wait until an explicit path or one unambiguous CH340 is available."""
    deadline = clock() + wait_seconds
    last_error = None
    while True:
        try:
            if host == AUTO_PORT:
                resolved = resolver(host)
                if Path(resolved).exists():
                    return resolved, None
                last_error = f"resolved path not found: {resolved}"
            elif Path(host).exists():
                return host, None
            else:
                last_error = f"path not found: {host}"
        except RuntimeError as exc:
            last_error = str(exc)
        remaining = deadline - clock()
        if remaining <= 0:
            return None, last_error
        sleep(min(poll_seconds, remaining))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="read-only preflight for goalkeeper-test systemd service")
    parser.add_argument("--model", required=True)
    parser.add_argument("--camera", default="/dev/video0")
    parser.add_argument("--host")
    parser.add_argument("--wait", type=float, default=30.0)
    args = parser.parse_args(argv)
    if not 0.0 <= args.wait <= MAX_WAIT_SECONDS:
        parser.error("--wait must be in [0, 120]")
    return args


def main(argv=None):
    args = parse_args(argv)
    model = Path(args.model)
    if not model.is_file():
        print(f"PREFLIGHT ERROR: model not found: {model.resolve()}")
        return 2
    if not wait_for_path(args.camera, args.wait):
        print(
            f"PREFLIGHT ERROR: camera not ready after {args.wait:.1f}s: "
            f"{args.camera}")
        return 2
    resolved_host = None
    if args.host:
        resolved_host, error = wait_for_host(args.host, args.wait)
        if resolved_host is None:
            print(
                f"PREFLIGHT ERROR: HOST link not ready after "
                f"{args.wait:.1f}s: {error}")
            return 2
    host = f" host={resolved_host}" if resolved_host else ""
    print(f"PREFLIGHT OK: model={model} camera={args.camera}{host}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
