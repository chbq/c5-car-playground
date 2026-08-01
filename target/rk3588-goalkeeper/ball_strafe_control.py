"""Pixel-space ball lateral controller and bounded HOST test session."""

from dataclasses import dataclass
from enum import Enum
import math
import time


class BallStrafeState(Enum):
    NO_TARGET = "NO_TARGET"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CENTERED = "CENTERED"
    TRACKING = "TRACKING"


@dataclass(frozen=True)
class BallStrafeConfig:
    """Tunable pixel controller values for the Phase 5B test."""

    deadband: float = 0.10
    min_confidence: float = 0.35
    proportional_gain: float = 1000.0
    min_vy: int = 250
    max_vy: int = 800
    max_step: int = 120
    lateral_sign: int = -1

    def validate(self):
        if not 0.0 <= self.deadband < 1.0:
            raise ValueError("deadband must be in [0, 1)")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be in [0, 1]")
        if not math.isfinite(self.proportional_gain) or self.proportional_gain <= 0:
            raise ValueError("proportional_gain must be positive")
        if not 0 <= self.min_vy <= self.max_vy <= 1000:
            raise ValueError("vy limits must satisfy 0 <= min <= max <= 1000")
        if not 1 <= self.max_step <= 1000:
            raise ValueError("max_step must be in [1, 1000]")
        if self.lateral_sign not in (-1, 1):
            raise ValueError("lateral_sign must be -1 or 1")


@dataclass(frozen=True)
class BallStrafeDecision:
    state: BallStrafeState
    error: float
    vy: int
    x: int | None
    confidence: float | None

    @property
    def has_target(self):
        return self.state in (BallStrafeState.CENTERED, BallStrafeState.TRACKING)


class BallStrafeController:
    """Convert horizontal ball position into a bounded lateral command."""

    def __init__(self, config=None):
        self.config = config or BallStrafeConfig()
        self.config.validate()
        self._last_vy = 0

    def reset(self):
        self._last_vy = 0

    def update(self, x, confidence, frame_width):
        if frame_width <= 0:
            raise ValueError("frame_width must be positive")
        if x is None or confidence is None:
            return self._stop_decision(BallStrafeState.NO_TARGET, x, confidence)
        if not math.isfinite(float(x)) or not math.isfinite(float(confidence)):
            return self._stop_decision(BallStrafeState.NO_TARGET, None, None)
        if confidence < self.config.min_confidence:
            return self._stop_decision(
                BallStrafeState.LOW_CONFIDENCE, int(x), float(confidence))

        error = (float(x) - frame_width / 2.0) / (frame_width / 2.0)
        error = max(-1.0, min(1.0, error))
        if abs(error) <= self.config.deadband:
            self._last_vy = 0
            return BallStrafeDecision(
                BallStrafeState.CENTERED, error, 0, int(x), float(confidence))

        magnitude = int(round(abs(error) * self.config.proportional_gain))
        magnitude = max(self.config.min_vy, min(self.config.max_vy, magnitude))
        target = (1 if error > 0 else -1) * self.config.lateral_sign * magnitude

        # A sign reversal crosses zero before accelerating the other way.
        if self._last_vy != 0 and target * self._last_vy < 0:
            output = 0
        else:
            lower = self._last_vy - self.config.max_step
            upper = self._last_vy + self.config.max_step
            output = max(lower, min(upper, target))

        self._last_vy = int(output)
        return BallStrafeDecision(
            BallStrafeState.TRACKING, error, self._last_vy,
            int(x), float(confidence))

    def _stop_decision(self, state, x, confidence):
        self._last_vy = 0
        return BallStrafeDecision(state, 0.0, 0, x, confidence)


class BallStrafeSession:
    """Run a dry or explicitly armed 20 Hz ball-strafe session."""

    def __init__(self, controller, link=None, execute=False,
                 control_period=0.05, acquire_cycles=3, lost_timeout=0.5,
                 hold_arm_until_duration=False):
        if execute and link is None:
            raise ValueError("execute mode requires a motion link")
        if control_period <= 0:
            raise ValueError("control_period must be positive")
        if acquire_cycles < 1:
            raise ValueError("acquire_cycles must be positive")
        if lost_timeout <= 0:
            raise ValueError("lost_timeout must be positive")

        self.controller = controller
        self.link = link
        self.execute = execute
        self.control_period = control_period
        self.acquire_cycles = acquire_cycles
        self.lost_timeout = lost_timeout
        self.hold_arm_until_duration = hold_arm_until_duration
        self.armed = False
        self.paused = False
        self.pause_count = 0
        self.finished = False
        self.stop_reason = None
        self.last_decision = None
        self.last_sent_vy = None
        self._last_tick = None
        self._last_target_time = None
        self._acquire_count = 0

    def tick(self, observation, frame_width, now=None):
        """Process at most one control cycle and return its decision."""
        if self.finished:
            return None
        now = time.monotonic() if now is None else now
        if (self._last_tick is not None and
                now - self._last_tick + 1e-12 < self.control_period):
            return None
        self._last_tick = now

        if observation is None:
            x, confidence = None, None
        else:
            x, confidence = observation.x, observation.conf
        decision = self.controller.update(x, confidence, frame_width)
        self.last_decision = decision

        if decision.has_target:
            self._last_target_time = now
            self._acquire_count += 1
        else:
            self._acquire_count = 0

        if not self.execute:
            return decision

        try:
            if not self.armed:
                if self._acquire_count < self.acquire_cycles:
                    return decision
                self.link.arm()
                self.armed = True
                self.paused = False
            elif (decision.has_target and
                  self._acquire_count >= self.acquire_cycles):
                self.paused = False

            if (not decision.has_target and self._last_target_time is not None and
                    now - self._last_target_time >= self.lost_timeout):
                if self.hold_arm_until_duration:
                    self._hold_zero_for_target_loss()
                else:
                    self.stop("target-lost")
                    return decision

            # Require consecutive confirmation after every target loss.
            vy = (decision.vy
                  if self._acquire_count >= self.acquire_cycles else 0)
            self.link.set_twist(0, vy, 0)
            self.last_sent_vy = vy
            return decision
        except Exception:
            self.stop("link-error")
            raise

    def _hold_zero_for_target_loss(self):
        if self.paused:
            return
        self.controller.reset()
        self.last_sent_vy = 0
        self.paused = True
        self.pause_count += 1
        self._acquire_count = 0

    def stop(self, reason):
        """Stop once; execute mode sends the global STOP command."""
        if self.finished:
            return
        self.finished = True
        self.stop_reason = reason
        self.paused = False
        self.controller.reset()
        if self.execute:
            self.link.safe_stop()
            self.last_sent_vy = 0
        self.armed = False
