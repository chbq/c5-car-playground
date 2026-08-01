"""Side-camera ball controller for horizontal, depth and yaw tracking."""

from dataclasses import dataclass
from enum import Enum
import math
import time

from ball_yaw_control import BallYawConfig, BallYawController


class BallFollowState(Enum):
    NO_TARGET = "NO_TARGET"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PREDICTING = "PREDICTING"
    CENTERED = "CENTERED"
    TRACKING = "TRACKING"


class BallFovZone(Enum):
    OFF = "OFF"
    CENTER = "CENTER"
    TRACK = "TRACK"
    EDGE = "EDGE"
    PREDICTING = "PREDICTING"


@dataclass(frozen=True)
class BallFollowConfig:
    """Phase 5C pursuit parameters with a bounded mecanum budget."""

    deadband: float = 0.10
    min_confidence: float = 0.35
    vx_gain: float = 1000.0
    min_vx: int = 250
    max_vx: int = 800
    max_vx_step: int = 120
    vx_sign: int = -1
    target_box_ratio: float = 0.35
    distance_deadband: float = 0.05
    vy_gain: float = 4000.0
    min_vy: int = 200
    max_vy: int = 600
    max_vy_step: int = 100
    vy_sign: int = 1
    yaw_gain: float = 220.0
    min_wz: int = 40
    max_wz: int = 180
    max_wz_step: int = 20
    yaw_sign: int = 1
    fov_enabled: bool = False
    fov_error_alpha: float = 0.55
    fov_rate_alpha: float = 0.35
    fov_prediction_horizon: float = 0.15
    fov_predict_hold: float = 0.15
    fov_edge_enter: float = 0.55
    fov_edge_exit: float = 0.30
    fov_translation_scale: float = 0.25

    def validate(self):
        BallYawConfig(
            deadband=self.deadband,
            min_confidence=self.min_confidence,
            proportional_gain=self.yaw_gain,
            min_wz=self.min_wz,
            max_wz=self.max_wz,
            max_step=self.max_wz_step,
            yaw_sign=self.yaw_sign,
        ).validate()
        if not math.isfinite(self.vx_gain) or self.vx_gain <= 0:
            raise ValueError("vx_gain must be positive")
        if not 0 < self.min_vx <= self.max_vx <= 1000:
            raise ValueError("vx limits must satisfy 0 < min <= max <= 1000")
        if not 0 < self.max_vx_step <= 1000:
            raise ValueError("max_vx_step must be in [1, 1000]")
        if self.vx_sign not in (-1, 1):
            raise ValueError("vx_sign must be -1 or 1")
        if not 0.0 < self.target_box_ratio < 1.0:
            raise ValueError("target_box_ratio must be in (0, 1)")
        if not 0.0 < self.distance_deadband < self.target_box_ratio:
            raise ValueError(
                "distance_deadband must be in (0, target_box_ratio)")
        if not math.isfinite(self.vy_gain) or self.vy_gain <= 0:
            raise ValueError("vy_gain must be positive")
        if not 0 < self.min_vy <= self.max_vy <= 1000:
            raise ValueError("vy limits must satisfy 0 < min <= max <= 1000")
        if not 0 < self.max_vy_step <= 1000:
            raise ValueError("max_vy_step must be in [1, 1000]")
        if self.vy_sign not in (-1, 1):
            raise ValueError("vy_sign must be -1 or 1")
        if not 0.0 < self.fov_error_alpha <= 1.0:
            raise ValueError("fov_error_alpha must be in (0, 1]")
        if not 0.0 < self.fov_rate_alpha <= 1.0:
            raise ValueError("fov_rate_alpha must be in (0, 1]")
        if not 0.0 <= self.fov_prediction_horizon <= 0.5:
            raise ValueError("fov_prediction_horizon must be in [0, 0.5]")
        if not 0.0 <= self.fov_predict_hold <= 0.2:
            raise ValueError("fov_predict_hold must be in [0, 0.2]")
        if not 0.0 < self.fov_edge_exit < self.fov_edge_enter < 1.0:
            raise ValueError("fov edge thresholds must satisfy 0 < exit < enter < 1")
        if not 0.0 <= self.fov_translation_scale <= 1.0:
            raise ValueError("fov_translation_scale must be in [0, 1]")


@dataclass(frozen=True)
class BallFollowDecision:
    state: BallFollowState
    error: float
    distance_error: float
    box_ratio: float
    vx: int
    vy: int
    wz: int
    x: int | None
    box_height: int | None
    confidence: float | None
    zone: BallFovZone = BallFovZone.OFF
    filtered_error: float = 0.0
    error_rate: float = 0.0
    predicted_error: float = 0.0
    target_age: float = 0.0
    lost_frames: int = 0
    predicted_only: bool = False

    @property
    def has_target(self):
        return self.state in (
            BallFollowState.CENTERED,
            BallFollowState.TRACKING,
        )


class BallFollowController:
    """Track image x with vx/wz and apparent distance with vy."""

    def __init__(self, config=None):
        self.config = config or BallFollowConfig()
        self.config.validate()
        self._yaw = BallYawController(BallYawConfig(
            deadband=self.config.deadband,
            min_confidence=self.config.min_confidence,
            proportional_gain=self.config.yaw_gain,
            min_wz=self.config.min_wz,
            max_wz=self.config.max_wz,
            max_step=self.config.max_wz_step,
            yaw_sign=self.config.yaw_sign,
        ))
        self._last_vx = 0
        self._last_vy = 0
        self._filtered_error = None
        self._error_rate = 0.0
        self._last_filter_time = None
        self._last_observation_time = None
        self._last_confidence = None
        self._fov_zone = BallFovZone.OFF
        self._lost_frames = 0

    def reset(self):
        self._yaw.reset()
        self._last_vx = 0
        self._last_vy = 0
        self._filtered_error = None
        self._error_rate = 0.0
        self._last_filter_time = None
        self._last_observation_time = None
        self._last_confidence = None
        self._fov_zone = BallFovZone.OFF
        self._lost_frames = 0

    def update(self, x, box_height, confidence, frame_width, frame_height,
               now=None):
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")
        now = time.monotonic() if now is None else float(now)
        if not math.isfinite(now):
            raise ValueError("now must be finite")

        if x is None or box_height is None or confidence is None:
            return self._handle_loss(
                BallFollowState.NO_TARGET, frame_width, now)
        if not all(math.isfinite(float(value)) for value in (
                x, box_height, confidence)):
            return self._handle_loss(
                BallFollowState.NO_TARGET, frame_width, now)
        if box_height <= 0:
            return self._handle_loss(
                BallFollowState.NO_TARGET, frame_width, now,
                x=int(x), box_height=int(box_height),
                confidence=float(confidence))
        if confidence < self.config.min_confidence:
            return self._handle_loss(
                BallFollowState.LOW_CONFIDENCE, frame_width, now,
                x=int(x), box_height=int(box_height),
                confidence=float(confidence))

        raw_error = self._normalized_error(x, frame_width)
        if self.config.fov_enabled:
            filtered_error, error_rate = self._filter_error(raw_error, now)
            predicted_error = self._clamp_error(
                filtered_error +
                error_rate * self.config.fov_prediction_horizon)
            zone = self._select_fov_zone(filtered_error, predicted_error)
            yaw_error = (
                predicted_error if zone == BallFovZone.EDGE
                else filtered_error)
        else:
            filtered_error = raw_error
            error_rate = 0.0
            predicted_error = raw_error
            zone = BallFovZone.OFF
            yaw_error = raw_error

        yaw_x = frame_width * (1.0 + yaw_error) / 2.0
        yaw = self._yaw.update(yaw_x, confidence, frame_width)
        box_ratio = max(0.0, min(1.0, float(box_height) / frame_height))
        distance_error = self.config.target_box_ratio - box_ratio

        if abs(filtered_error) <= self.config.deadband:
            target_vx = 0
        else:
            magnitude = int(round(abs(filtered_error) * self.config.vx_gain))
            magnitude = max(self.config.min_vx, min(self.config.max_vx, magnitude))
            target_vx = (
                (1 if filtered_error > 0 else -1) *
                self.config.vx_sign * magnitude)

        if abs(distance_error) <= self.config.distance_deadband:
            target_vy = 0
        else:
            magnitude = int(round(abs(distance_error) * self.config.vy_gain))
            magnitude = max(self.config.min_vy, min(self.config.max_vy, magnitude))
            target_vy = (
                (1 if distance_error > 0 else -1) *
                self.config.vy_sign * magnitude)

        if zone == BallFovZone.EDGE:
            target_vx = int(round(
                target_vx * self.config.fov_translation_scale))
            target_vy = int(round(
                target_vy * self.config.fov_translation_scale))
            vx_limit = int(round(
                self.config.max_vx * self.config.fov_translation_scale))
            vy_limit = int(round(
                self.config.max_vy * self.config.fov_translation_scale))
            self._last_vx = max(-vx_limit, min(vx_limit, self._last_vx))
            self._last_vy = max(-vy_limit, min(vy_limit, self._last_vy))

        vx = self._ramp_vx(target_vx)
        vy = self._ramp_vy(target_vy)
        if zone == BallFovZone.EDGE:
            vx, vy, wz = self._limit_axes_yaw_first(vx, vy, yaw.wz)
        else:
            vx, vy, wz = self._limit_axes(vx, vy, yaw.wz)

        if (abs(filtered_error) <= self.config.deadband and
                abs(distance_error) <= self.config.distance_deadband):
            state = BallFollowState.CENTERED
        else:
            state = BallFollowState.TRACKING
        self._last_observation_time = now
        self._last_confidence = float(confidence)
        self._lost_frames = 0
        return BallFollowDecision(
            state=state,
            error=raw_error,
            distance_error=distance_error,
            box_ratio=box_ratio,
            vx=vx,
            vy=vy,
            wz=wz,
            x=int(x),
            box_height=int(box_height),
            confidence=float(confidence),
            zone=zone,
            filtered_error=filtered_error,
            error_rate=error_rate,
            predicted_error=predicted_error,
        )

    @staticmethod
    def _normalized_error(x, frame_width):
        return BallFollowController._clamp_error(
            (float(x) - frame_width / 2.0) / (frame_width / 2.0))

    @staticmethod
    def _clamp_error(value):
        return max(-1.0, min(1.0, float(value)))

    def _filter_error(self, raw_error, now):
        if self._filtered_error is None:
            filtered = raw_error
            rate = 0.0
        else:
            previous = self._filtered_error
            alpha = self.config.fov_error_alpha
            filtered = alpha * raw_error + (1.0 - alpha) * previous
            dt = now - self._last_filter_time
            if 1e-6 < dt <= 0.5:
                raw_rate = (filtered - previous) / dt
                rate_alpha = self.config.fov_rate_alpha
                rate = (
                    rate_alpha * raw_rate +
                    (1.0 - rate_alpha) * self._error_rate)
            else:
                rate = 0.0
        self._filtered_error = self._clamp_error(filtered)
        self._error_rate = rate
        self._last_filter_time = now
        return self._filtered_error, self._error_rate

    def _select_fov_zone(self, filtered_error, predicted_error):
        magnitude = abs(predicted_error)
        if (self._fov_zone == BallFovZone.EDGE and
                magnitude >= self.config.fov_edge_exit):
            zone = BallFovZone.EDGE
        elif magnitude >= self.config.fov_edge_enter:
            zone = BallFovZone.EDGE
        elif abs(filtered_error) <= self.config.deadband:
            zone = BallFovZone.CENTER
        else:
            zone = BallFovZone.TRACK
        self._fov_zone = zone
        return zone

    def _handle_loss(self, state, frame_width, now, x=None,
                     box_height=None, confidence=None):
        self._lost_frames += 1
        if (self.config.fov_enabled and
                self._last_observation_time is not None and
                self._last_confidence is not None):
            age = max(0.0, now - self._last_observation_time)
            if age <= self.config.fov_predict_hold:
                predicted_error = self._clamp_error(
                    self._filtered_error + self._error_rate * age)
                yaw_x = frame_width * (1.0 + predicted_error) / 2.0
                yaw = self._yaw.update(
                    yaw_x, self._last_confidence, frame_width)
                self._last_vx = 0
                self._last_vy = 0
                self._fov_zone = BallFovZone.PREDICTING
                return BallFollowDecision(
                    state=BallFollowState.PREDICTING,
                    error=0.0,
                    distance_error=0.0,
                    box_ratio=0.0,
                    vx=0,
                    vy=0,
                    wz=yaw.wz,
                    x=x,
                    box_height=box_height,
                    confidence=confidence,
                    zone=BallFovZone.PREDICTING,
                    filtered_error=self._filtered_error,
                    error_rate=self._error_rate,
                    predicted_error=predicted_error,
                    target_age=age,
                    lost_frames=self._lost_frames,
                    predicted_only=True,
                )
        return self._stop_decision(
            state, x=x, box_height=box_height, confidence=confidence)

    def _ramp_vx(self, target):
        if target == 0:
            self._last_vx = 0
            return 0
        # A side change crosses zero before translating the other way.
        if self._last_vx != 0 and target * self._last_vx < 0:
            self._last_vx = 0
            return 0
        lower = self._last_vx - self.config.max_vx_step
        upper = self._last_vx + self.config.max_vx_step
        self._last_vx = int(max(lower, min(upper, target)))
        return self._last_vx

    def _ramp_vy(self, target):
        if target == 0:
            self._last_vy = 0
            return 0
        if self._last_vy != 0 and target * self._last_vy < 0:
            self._last_vy = 0
            return 0
        lower = self._last_vy - self.config.max_vy_step
        upper = self._last_vy + self.config.max_vy_step
        self._last_vy = int(max(lower, min(upper, target)))
        return self._last_vy

    @staticmethod
    def _limit_axes(vx, vy, wz):
        total = abs(vx) + abs(vy) + abs(wz)
        if total <= 1000:
            return vx, vy, wz
        return tuple(int(axis * 1000 / total) for axis in (vx, vy, wz))

    @staticmethod
    def _limit_axes_yaw_first(vx, vy, wz):
        wz = max(-1000, min(1000, int(wz)))
        translation_budget = 1000 - abs(wz)
        translation_total = abs(vx) + abs(vy)
        if translation_total <= translation_budget:
            return vx, vy, wz
        if translation_total == 0:
            return 0, 0, wz
        return (
            int(vx * translation_budget / translation_total),
            int(vy * translation_budget / translation_total),
            wz,
        )

    def _stop_decision(self, state, x=None, box_height=None, confidence=None):
        lost_frames = self._lost_frames
        self.reset()
        self._lost_frames = lost_frames
        return BallFollowDecision(
            state=state,
            error=0.0,
            distance_error=0.0,
            box_ratio=0.0,
            vx=0,
            vy=0,
            wz=0,
            x=x,
            box_height=box_height,
            confidence=confidence,
            lost_frames=lost_frames,
        )


class BallFollowSession:
    """Run a dry or explicitly armed 20 Hz ball-pursuit session."""

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
        self.last_sent_vx = None
        self.last_sent_vy = None
        self.last_sent_wz = None
        self._last_tick = None
        self._last_target_time = None
        self._acquire_count = 0

    def tick(self, observation, frame_width, frame_height, now=None):
        """Process at most one control cycle and return its decision."""
        if self.finished:
            return None
        now = time.monotonic() if now is None else now
        if (self._last_tick is not None and
                now - self._last_tick + 1e-12 < self.control_period):
            return None
        self._last_tick = now

        if observation is None:
            x, box_height, confidence = None, None, None
        else:
            x = observation.x
            box_height = getattr(observation, "height", None)
            confidence = observation.conf
        decision = self.controller.update(
            x, box_height, confidence, frame_width, frame_height, now=now)
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

            confirmed = self._acquire_count >= self.acquire_cycles
            if confirmed:
                vx, vy, wz = decision.vx, decision.vy, decision.wz
            elif self.armed and decision.predicted_only:
                # A fresh prediction may rotate briefly, but never translate.
                vx, vy, wz = 0, 0, decision.wz
            else:
                vx, vy, wz = 0, 0, 0
            self.link.set_twist(vx, vy, wz)
            self.last_sent_vx = vx
            self.last_sent_vy = vy
            self.last_sent_wz = wz
            return decision
        except Exception:
            self.stop("link-error")
            raise

    def _hold_zero_for_target_loss(self):
        if self.paused:
            return
        self.controller.reset()
        self.last_sent_vx = 0
        self.last_sent_vy = 0
        self.last_sent_wz = 0
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
            self.last_sent_vx = 0
            self.last_sent_vy = 0
            self.last_sent_wz = 0
        self.armed = False
