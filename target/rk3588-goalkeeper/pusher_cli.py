"""Manual Orange Pi backup CLI for a ZDT Emm pusher motor."""

import argparse

from zdt_pusher_control import PusherCycleConfig, run_bounded_cycles
from zdt_pusher_link import PusherLinkError, ZdtPusherLink


def bounded_int(name, minimum, maximum):
    def parse(value):
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be in [{minimum}, {maximum}]")
        return parsed
    return parse


def bounded_float(name, minimum, maximum):
    def parse(value):
        parsed = float(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be in [{minimum}, {maximum}]")
        return parsed
    return parse


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="ZDT pusher backup utility; default action is status query")
    parser.add_argument(
        "--port", default="/dev/c5-pusher",
        help="explicit stable pusher serial path; never auto-discovers ttyUSB")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--address", type=bounded_int("address", 1, 255), default=1)
    subparsers = parser.add_subparsers(dest="action")
    subparsers.add_parser("query", help="read enable/reached/stall flags")
    subparsers.add_parser("stop", help="send immediate STOP; does not disable")

    cycle = subparsers.add_parser(
        "cycle", help="run bounded out/back relative-position cycles")
    cycle.add_argument("--stroke-pulses", required=True,
                       type=bounded_int("stroke_pulses", 1, 3200))
    cycle.add_argument("--speed-rpm", required=True,
                       type=bounded_int("speed_rpm", 1, 300))
    cycle.add_argument("--acceleration", required=True,
                       type=bounded_int("acceleration", 1, 200))
    cycle.add_argument("--cycles", type=bounded_int("cycles", 1, 10),
                       default=1)
    cycle.add_argument("--outward-direction", choices=("cw", "ccw"),
                       required=True)
    cycle.add_argument("--segment-timeout",
                       type=bounded_float("segment_timeout", 0.2, 10.0),
                       default=3.0)
    cycle.add_argument("--idle-behavior", choices=("hold", "release"),
                       required=True,
                       help="hold keeps torque after STOP; release loosens shaft")
    cycle.add_argument(
        "--execute", action="store_true",
        help="required acknowledgement that cycle can move the pusher")
    return parser.parse_args(argv)


def format_status(status):
    return (
        f"raw=0x{status.raw:02X} enabled={status.enabled} "
        f"reached={status.reached} stalled={status.stalled} "
        f"protected={status.stall_protected} "
        f"left_high={status.left_limit_high} "
        f"right_high={status.right_limit_high} power_lost={status.power_lost}"
    )


def main(argv=None, link_factory=ZdtPusherLink):
    args = parse_args(argv)
    action = args.action or "query"
    if action == "cycle" and not args.execute:
        print("ERROR: cycle requires --execute")
        return 1
    try:
        with link_factory(
                args.port, baudrate=args.baud, address=args.address) as link:
            if action == "query":
                print(format_status(link.query_status()))
                return 0
            if action == "stop":
                link.stop()
                print("STOP acknowledged; enable/hold state was not changed")
                return 0
            config = PusherCycleConfig(
                stroke_pulses=args.stroke_pulses,
                speed_rpm=args.speed_rpm,
                acceleration=args.acceleration,
                cycles=args.cycles,
                outward_direction=(
                    0 if args.outward_direction == "cw" else 1),
                segment_timeout=args.segment_timeout,
                idle_behavior=args.idle_behavior,
            )
            result = run_bounded_cycles(link, config)
            print(
                f"completed={result.completed_cycles} "
                f"holding={result.holding} "
                f"status=({format_status(result.final_status)})")
            return 0
    except (PusherLinkError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
