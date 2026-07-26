"""Bounded manual CLI for raised-chassis C5 HOST link testing."""

import argparse
import time

from motion_link import MotionLink, MotionLinkError

CLI_AXIS_LIMIT = 200
MAX_DURATION_S = 2.0
COMMAND_PERIOD_S = 0.05


def format_status(status):
    return (
        f"seq={status.sequence} result={status.result.name} "
        f"mode={status.mode.name} host={status.host_state.name} "
        f"motion={status.motion_state.name} errors={status.error_count}"
    )


def bounded_axis(value):
    value = int(value)
    if not -CLI_AXIS_LIMIT <= value <= CLI_AXIS_LIMIT:
        raise argparse.ArgumentTypeError(
            f"axis must be in [-{CLI_AXIS_LIMIT}, {CLI_AXIS_LIMIT}]"
        )
    return value


def bounded_duration(value):
    value = float(value)
    if not 0.05 <= value <= MAX_DURATION_S:
        raise argparse.ArgumentTypeError("duration must be in [0.05, 2.0] seconds")
    return value


def parse_args():
    parser = argparse.ArgumentParser(
        description="C5 HOST UART utility; no subcommand performs QUERY only."
    )
    parser.add_argument(
        "--port", default="auto",
        help="serial path; auto discovers one CH340 device",
    )
    parser.add_argument("--baud", type=int, default=115200)
    subparsers = parser.add_subparsers(dest="action")
    subparsers.add_parser("query", help="read current STM32 control state")
    subparsers.add_parser("stop", help="send STOP and disarm all control sources")
    move = subparsers.add_parser("move", help="run one bounded 20 Hz twist test")
    move.add_argument("--vx", type=bounded_axis, default=0)
    move.add_argument("--vy", type=bounded_axis, default=0)
    move.add_argument("--wz", type=bounded_axis, default=0)
    move.add_argument("--duration", type=bounded_duration, default=0.5)
    move.add_argument(
        "--execute",
        action="store_true",
        help="required acknowledgement that this command can move the car",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    action = args.action or "query"
    try:
        with MotionLink(port=args.port, baudrate=args.baud) as link:
            print(format_status(link.query()))
            if action == "query":
                return 0
            if action == "stop":
                print(format_status(link.stop()))
                return 0
            if not args.execute:
                raise MotionLinkError("move requires --execute")

            print(format_status(link.arm()))
            deadline = time.monotonic() + args.duration
            try:
                while time.monotonic() < deadline:
                    started = time.monotonic()
                    status = link.set_twist(args.vx, args.vy, args.wz)
                    remaining = COMMAND_PERIOD_S - (time.monotonic() - started)
                    if remaining > 0:
                        time.sleep(remaining)
                print(format_status(status))
            finally:
                stopped = link.safe_stop()
                if stopped is not None:
                    print(format_status(stopped))
        return 0
    except (MotionLinkError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
