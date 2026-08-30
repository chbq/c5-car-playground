"""Bounded backup cycle runner for the ZDT pusher motor."""

from dataclasses import dataclass
import time

from zdt_pusher_link import PusherLinkError


@dataclass(frozen=True)
class PusherCycleConfig:
    """Explicit hardware-unverified limits for one bounded manual run."""

    stroke_pulses: int
    speed_rpm: int
    acceleration: int
    cycles: int
    outward_direction: int
    segment_timeout: float
    poll_period: float = 0.05
    idle_behavior: str = ""

    def validate(self):
        if not 1 <= self.stroke_pulses <= 3200:
            raise ValueError("stroke_pulses must be in [1, 3200]")
        if not 1 <= self.speed_rpm <= 300:
            raise ValueError("speed_rpm must be in [1, 300]")
        if not 1 <= self.acceleration <= 200:
            raise ValueError("acceleration must be in [1, 200]")
        if not 1 <= self.cycles <= 10:
            raise ValueError("cycles must be in [1, 10]")
        if self.outward_direction not in (0, 1):
            raise ValueError("outward_direction must be 0 or 1")
        if not 0.2 <= self.segment_timeout <= 10.0:
            raise ValueError("segment_timeout must be in [0.2, 10.0]")
        if not 0.02 <= self.poll_period <= 0.2:
            raise ValueError("poll_period must be in [0.02, 0.2]")
        if self.idle_behavior not in ("hold", "release"):
            raise ValueError("idle_behavior must be hold or release")


@dataclass(frozen=True)
class PusherCycleResult:
    completed_cycles: int
    final_status: object
    holding: bool


def wait_until_reached(link, timeout, poll_period=0.05,
                       clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        status = link.query_status()
        if status.stalled or status.stall_protected:
            raise PusherLinkError(
                "pusher reported stall or stall protection")
        if status.reached:
            return status
        remaining = deadline - clock()
        if remaining <= 0:
            raise PusherLinkError("pusher segment did not reach target in time")
        sleep(min(poll_period, remaining))


def run_bounded_cycles(link, config, clock=time.monotonic, sleep=time.sleep):
    """Run explicit out/back position segments and always issue final STOP."""
    config.validate()
    completed = 0
    final_status = None
    try:
        final_status = link.query_status()
        if final_status.stalled or final_status.stall_protected:
            raise PusherLinkError("pusher is faulted before cycle start")
        link.set_enabled(True)
        for _ in range(config.cycles):
            link.move_relative(
                config.outward_direction,
                config.speed_rpm,
                config.acceleration,
                config.stroke_pulses,
            )
            wait_until_reached(
                link, config.segment_timeout, config.poll_period,
                clock=clock, sleep=sleep)
            link.move_relative(
                1 - config.outward_direction,
                config.speed_rpm,
                config.acceleration,
                config.stroke_pulses,
            )
            final_status = wait_until_reached(
                link, config.segment_timeout, config.poll_period,
                clock=clock, sleep=sleep)
            completed += 1
    finally:
        link.safe_stop()
        if config.idle_behavior == "release":
            link.safe_disable()

    return PusherCycleResult(
        completed_cycles=completed,
        final_status=final_status,
        holding=config.idle_behavior == "hold",
    )
