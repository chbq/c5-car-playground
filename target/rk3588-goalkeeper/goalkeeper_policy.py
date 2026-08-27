"""Analytic goalkeeper policy over timestamped relative observations."""

from dataclasses import dataclass
from enum import Enum
import math


class GoalkeeperState(Enum):
    DISABLED = "DISABLED"
    ANCHORING = "ANCHORING"
    HOLD = "HOLD"
    BALL_WATCH = "BALL_WATCH"
    INTERCEPT = "INTERCEPT"
    CLOSE_BLOCK = "CLOSE_BLOCK"
    RECOVER = "RECOVER"
    BALL_LOST = "BALL_LOST"
    ANCHOR_LOST = "ANCHOR_LOST"
    FAULT = "FAULT"


class LocalizationCapability(Enum):
    INVALID = "INVALID"
    GOAL_RELATIVE = "GOAL_RELATIVE"


class PusherIntent(Enum):
    IDLE = "IDLE"
    CYCLE = "CYCLE"


class BallRange(Enum):
    NONE = "NONE"
    FAR = "FAR"
    WARNING = "WARNING"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class VisualObservation:
    """One detector observation in original-frame pixel coordinates."""

    x: float
    y: float
    width: float
    height: float
    confidence: float
    captured_at: float
    top_width: float | None = None

    @property
    def area(self):
        return self.width * self.height

    def is_valid(self):
        values = (
            self.x, self.y, self.width, self.height,
            self.confidence, self.captured_at,
        )
        if not all(math.isfinite(float(value)) for value in values):
            return False
        if self.width <= 0 or self.height <= 0:
            return False
        if not 0.0 <= self.confidence <= 1.0:
            return False
        if self.top_width is not None:
            if not math.isfinite(float(self.top_width)) or self.top_width <= 0:
                return False
        return True


@dataclass(frozen=True)
class PerceptionFrame:
    """Timestamped ball and opponent-goal observations for one frame."""

    frame_id: int
    captured_at: float
    processed_at: float
    frame_width: int
    frame_height: int
    ball: VisualObservation | None = None
    opponent_goal: VisualObservation | None = None

    def is_valid(self):
        if self.frame_id < 0 or self.frame_width <= 0 or self.frame_height <= 0:
            return False
        if not all(math.isfinite(float(value)) for value in (
                self.captured_at, self.processed_at)):
            return False
        if self.processed_at < self.captured_at:
            return False
        for observation in (self.ball, self.opponent_goal):
            if observation is not None and not observation.is_valid():
                return False
        return True


@dataclass(frozen=True)
class MotionIntent:
    """Candidate C5 command produced by the existing camera controller."""

    vx: int = 0
    vy: int = 0
    wz: int = 0


@dataclass(frozen=True)
class GoalkeeperConfig:
    """Calibrated pixel thresholds and bounded goalkeeper outputs."""

    min_ball_confidence: float = 0.35
    min_goal_confidence: float = 0.45
    max_observation_age: float = 0.25
    anchor_cycles: int = 3
    goal_center_deadband: float = 0.10
    goal_center_soft_limit: float = 0.45
    goal_center_hard_limit: float = 0.70
    goal_yaw_gain: float = 220.0
    min_goal_wz: int = 40
    max_goal_wz: int = 160
    intercept_enter_area: float = 1500.0
    intercept_exit_area: float = 1200.0
    block_enter_area: float = 8000.0
    block_exit_area: float = 6500.0
    max_intercept_vx: int = 300
    max_intercept_vy: int = 250
    max_intercept_wz: int = 180
    decision_ttl: float = 0.10

    def validate(self):
        if not 0.0 <= self.min_ball_confidence <= 1.0:
            raise ValueError("min_ball_confidence must be in [0, 1]")
        if not 0.0 <= self.min_goal_confidence <= 1.0:
            raise ValueError("min_goal_confidence must be in [0, 1]")
        if not 0.0 < self.max_observation_age <= 1.0:
            raise ValueError("max_observation_age must be in (0, 1]")
        if self.anchor_cycles < 1:
            raise ValueError("anchor_cycles must be positive")
        if not (0.0 < self.goal_center_deadband <
                self.goal_center_soft_limit < self.goal_center_hard_limit < 1.0):
            raise ValueError("goal center limits must increase inside (0, 1)")
        if not math.isfinite(self.goal_yaw_gain) or self.goal_yaw_gain <= 0:
            raise ValueError("goal_yaw_gain must be positive")
        if not 0 < self.min_goal_wz <= self.max_goal_wz <= 1000:
            raise ValueError("goal yaw limits must satisfy 0 < min <= max <= 1000")
        if not (0.0 < self.intercept_exit_area < self.intercept_enter_area <
                self.block_exit_area < self.block_enter_area):
            raise ValueError("ball area thresholds and hysteresis are invalid")
        for value in (
                self.max_intercept_vx, self.max_intercept_vy,
                self.max_intercept_wz):
            if not 0 < value <= 1000:
                raise ValueError("intercept axis limits must be in [1, 1000]")
        if not 0.0 < self.decision_ttl <= self.max_observation_age:
            raise ValueError("decision_ttl must be positive and observation-bounded")


@dataclass(frozen=True)
class GoalkeeperDecision:
    state: GoalkeeperState
    capability: LocalizationCapability
    ball_range: BallRange
    vx: int
    vy: int
    wz: int
    pusher: PusherIntent
    valid_until: float
    reason: str
    goal_error: float = 0.0
    ball_area: float = 0.0


class GoalkeeperPolicy:
    """Gate an existing ball controller with an opponent-goal visual anchor."""

    def __init__(self, config=None):
        self.config = config or GoalkeeperConfig()
        self.config.validate()
        self.state = GoalkeeperState.DISABLED
        self._anchor_count = 0
        self._anchored = False
        self._ball_range = BallRange.NONE
        self._had_ball = False
        self._last_frame_id = None
        self._last_processed_at = None

    def reset(self):
        self.state = GoalkeeperState.DISABLED
        self._anchor_count = 0
        self._anchored = False
        self._ball_range = BallRange.NONE
        self._had_ball = False
        self._last_frame_id = None
        self._last_processed_at = None

    def update(self, frame, candidate=None, enabled=False):
        candidate = candidate or MotionIntent()
        if not enabled:
            self.reset()
            return self._decision(
                frame, GoalkeeperState.DISABLED,
                LocalizationCapability.INVALID, BallRange.NONE,
                reason="disabled")
        if not frame.is_valid():
            self.state = GoalkeeperState.FAULT
            return self._decision(
                frame, self.state, LocalizationCapability.INVALID,
                BallRange.NONE, reason="invalid-frame")
        if ((self._last_frame_id is not None and
             frame.frame_id <= self._last_frame_id) or
                (self._last_processed_at is not None and
                 frame.processed_at < self._last_processed_at)):
            self.state = GoalkeeperState.FAULT
            return self._decision(
                frame, self.state, LocalizationCapability.INVALID,
                BallRange.NONE, reason="non-monotonic-frame")
        self._last_frame_id = frame.frame_id
        self._last_processed_at = frame.processed_at

        goal = self._fresh(frame.opponent_goal, frame.processed_at,
                           self.config.min_goal_confidence)
        if goal is None:
            had_anchor = self._anchored
            self._anchor_count = 0
            self._anchored = False
            self._ball_range = BallRange.NONE
            state = (
                GoalkeeperState.ANCHOR_LOST if (
                    had_anchor or self.state == GoalkeeperState.ANCHOR_LOST)
                else GoalkeeperState.ANCHORING)
            self.state = state
            return self._decision(
                frame, state, LocalizationCapability.INVALID,
                BallRange.NONE, reason="opponent-goal-unavailable")

        self._anchor_count += 1
        if not self._anchored and self._anchor_count >= self.config.anchor_cycles:
            self._anchored = True
        goal_error = self._normalized_error(goal.x, frame.frame_width)
        if not self._anchored:
            self.state = GoalkeeperState.ANCHORING
            return self._decision(
                frame, self.state, LocalizationCapability.INVALID,
                BallRange.NONE, reason="confirming-opponent-goal",
                goal_error=goal_error)

        capability = LocalizationCapability.GOAL_RELATIVE
        if abs(goal_error) >= self.config.goal_center_hard_limit:
            self.state = GoalkeeperState.RECOVER
            return self._decision(
                frame, self.state, capability, BallRange.NONE,
                wz=self._goal_correction(goal_error),
                reason="goal-near-view-limit", goal_error=goal_error)

        ball = self._fresh(frame.ball, frame.processed_at,
                           self.config.min_ball_confidence)
        if ball is None:
            self._ball_range = BallRange.NONE
            if self._had_ball:
                self.state = GoalkeeperState.BALL_LOST
                wz = self._guard_yaw(candidate.wz, goal_error)
                return self._decision(
                    frame, self.state, capability, BallRange.NONE,
                    wz=wz, reason="ball-unavailable", goal_error=goal_error)
            if abs(goal_error) > self.config.goal_center_deadband:
                self.state = GoalkeeperState.RECOVER
                return self._decision(
                    frame, self.state, capability, BallRange.NONE,
                    wz=self._goal_correction(goal_error),
                    reason="holding-goal-center", goal_error=goal_error)
            self.state = GoalkeeperState.HOLD
            return self._decision(
                frame, self.state, capability, BallRange.NONE,
                reason="holding-relative-zone", goal_error=goal_error)

        self._had_ball = True
        self._ball_range = self._select_ball_range(ball.area)
        if self._ball_range == BallRange.CLOSE:
            self.state = GoalkeeperState.CLOSE_BLOCK
            return self._decision(
                frame, self.state, capability, self._ball_range,
                pusher=PusherIntent.CYCLE, reason="ball-close",
                goal_error=goal_error, ball_area=ball.area)

        if abs(goal_error) >= self.config.goal_center_soft_limit:
            self.state = GoalkeeperState.RECOVER
            return self._decision(
                frame, self.state, capability, self._ball_range,
                wz=self._goal_correction(goal_error),
                reason="goal-anchor-priority", goal_error=goal_error,
                ball_area=ball.area)

        if self._ball_range == BallRange.WARNING:
            self.state = GoalkeeperState.INTERCEPT
            vx, vy, wz = self._bounded_intercept(candidate)
            wz = self._guard_yaw(wz, goal_error)
            return self._decision(
                frame, self.state, capability, self._ball_range,
                vx=vx, vy=vy, wz=wz, reason="ball-warning-range",
                goal_error=goal_error, ball_area=ball.area)

        self.state = GoalkeeperState.BALL_WATCH
        return self._decision(
            frame, self.state, capability, self._ball_range,
            wz=self._guard_yaw(candidate.wz, goal_error),
            reason="ball-far", goal_error=goal_error,
            ball_area=ball.area)

    def _fresh(self, observation, now, min_confidence):
        if observation is None or not observation.is_valid():
            return None
        age = now - observation.captured_at
        if age < 0.0 or age > self.config.max_observation_age:
            return None
        if observation.confidence < min_confidence:
            return None
        return observation

    def _select_ball_range(self, area):
        if self._ball_range == BallRange.CLOSE:
            if area >= self.config.block_exit_area:
                return BallRange.CLOSE
        if area >= self.config.block_enter_area:
            return BallRange.CLOSE
        if self._ball_range == BallRange.WARNING:
            if area >= self.config.intercept_exit_area:
                return BallRange.WARNING
        if area >= self.config.intercept_enter_area:
            return BallRange.WARNING
        return BallRange.FAR

    def _goal_correction(self, error):
        magnitude = int(round(abs(error) * self.config.goal_yaw_gain))
        magnitude = max(
            self.config.min_goal_wz,
            min(self.config.max_goal_wz, magnitude))
        return magnitude if error > 0 else -magnitude

    def _guard_yaw(self, wz, goal_error):
        wz = self._clamp(int(wz), self.config.max_intercept_wz)
        if (abs(goal_error) >= self.config.goal_center_soft_limit * 0.8 and
                wz * goal_error < 0):
            return self._goal_correction(goal_error)
        return wz

    def _bounded_intercept(self, candidate):
        vx = self._clamp(int(candidate.vx), self.config.max_intercept_vx)
        vy = self._clamp(int(candidate.vy), self.config.max_intercept_vy)
        wz = self._clamp(int(candidate.wz), self.config.max_intercept_wz)
        total = abs(vx) + abs(vy) + abs(wz)
        if total <= 1000:
            return vx, vy, wz
        return tuple(int(axis * 1000 / total) for axis in (vx, vy, wz))

    @staticmethod
    def _normalized_error(x, frame_width):
        value = (float(x) - frame_width / 2.0) / (frame_width / 2.0)
        return max(-1.0, min(1.0, value))

    @staticmethod
    def _clamp(value, limit):
        return max(-limit, min(limit, value))

    def _decision(self, frame, state, capability, ball_range,
                  vx=0, vy=0, wz=0, pusher=PusherIntent.IDLE,
                  reason="", goal_error=0.0, ball_area=0.0):
        return GoalkeeperDecision(
            state=state,
            capability=capability,
            ball_range=ball_range,
            vx=int(vx),
            vy=int(vy),
            wz=int(wz),
            pusher=pusher,
            valid_until=frame.processed_at + self.config.decision_ttl,
            reason=reason,
            goal_error=float(goal_error),
            ball_area=float(ball_area),
        )
