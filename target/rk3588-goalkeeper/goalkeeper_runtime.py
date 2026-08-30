"""Hardware-free adapter from detector boxes to goalkeeper decisions."""

from dataclasses import dataclass
import math

from ball_follow_control import BallFollowConfig, BallFollowController
from goalkeeper_policy import (
    GoalkeeperPolicy,
    LocalizationCapability,
    MotionIntent,
    PerceptionFrame,
    VisualObservation,
)
from motion_link import MotionLinkNotArmedError


@dataclass(frozen=True)
class SyntheticGoalSpec:
    """Explicit test-only goal box in normalized image coordinates."""

    center_x: float
    center_y: float
    width: float
    height: float
    confidence: float = 1.0

    def validate(self):
        values = (
            self.center_x, self.center_y, self.width,
            self.height, self.confidence,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("synthetic goal values must be finite")
        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("synthetic goal size must be positive")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("synthetic goal confidence must be in [0, 1]")
        if (self.center_x - self.width / 2.0 < 0.0 or
                self.center_x + self.width / 2.0 > 1.0 or
                self.center_y - self.height / 2.0 < 0.0 or
                self.center_y + self.height / 2.0 > 1.0):
            raise ValueError("synthetic goal box must stay inside the image")

    def make_observation(self, frame_width, frame_height, captured_at):
        self.validate()
        return VisualObservation(
            x=self.center_x * frame_width,
            y=self.center_y * frame_height,
            width=self.width * frame_width,
            height=self.height * frame_height,
            confidence=self.confidence,
            captured_at=captured_at,
        )


def make_observation(info, captured_at):
    """Convert a tracker record into a capture-timestamped observation."""
    if info is None:
        return None
    return VisualObservation(
        x=info.x,
        y=info.y,
        width=info.width,
        height=info.height,
        confidence=info.conf,
        captured_at=captured_at,
    )


class GoalkeeperDryRunSession:
    """Run Phase 5C candidate control through the pure policy, without I/O."""

    def __init__(self, policy=None, candidate_controller=None, logger=None,
                 synthetic_goal=None):
        self.policy = policy or GoalkeeperPolicy()
        self.candidate_controller = (
            candidate_controller or BallFollowController(BallFollowConfig()))
        self.logger = logger
        if synthetic_goal is not None:
            synthetic_goal.validate()
        self.synthetic_goal = synthetic_goal

    def tick(self, frame_id, captured_at, processed_at, frame_width,
             frame_height, ball_info=None, goal_info=None):
        ball = make_observation(ball_info, captured_at)
        goal = (
            self.synthetic_goal.make_observation(
                frame_width, frame_height, processed_at)
            if self.synthetic_goal is not None else
            make_observation(goal_info, captured_at))
        candidate_decision = self.candidate_controller.update(
            None if ball is None else ball.x,
            None if ball is None else ball.height,
            None if ball is None else ball.confidence,
            frame_width,
            frame_height,
            now=processed_at,
        )
        candidate = MotionIntent(
            vx=candidate_decision.vx,
            vy=candidate_decision.vy,
            wz=candidate_decision.wz,
        )
        frame = PerceptionFrame(
            frame_id=frame_id,
            captured_at=captured_at,
            processed_at=processed_at,
            frame_width=frame_width,
            frame_height=frame_height,
            ball=ball,
            opponent_goal=goal,
        )
        decision = self.policy.update(frame, candidate, enabled=True)
        if self.logger is not None:
            self.logger.write(frame, candidate, decision)
        return frame, candidate, decision

    def reset(self):
        self.policy.reset()
        self.candidate_controller.reset()


class GoalkeeperMotionSession(GoalkeeperDryRunSession):
    """Send policy-approved decisions through an explicitly supplied link."""

    def __init__(self, link, policy=None, candidate_controller=None,
                 logger=None, control_period=0.05, acquire_cycles=3,
                 synthetic_goal=None):
        if link is None:
            raise ValueError("motion mode requires a motion link")
        if control_period <= 0:
            raise ValueError("control_period must be positive")
        if acquire_cycles < 1:
            raise ValueError("acquire_cycles must be positive")
        super().__init__(
            policy, candidate_controller, logger,
            synthetic_goal=synthetic_goal)
        self.link = link
        self.control_period = control_period
        self.acquire_cycles = acquire_cycles
        self.armed = False
        self.finished = False
        self.stop_reason = None
        self.last_sent_vx = 0
        self.last_sent_vy = 0
        self.last_sent_wz = 0
        self._acquire_count = 0
        self._last_send_at = None

    def tick(self, frame_id, captured_at, processed_at, frame_width,
             frame_height, ball_info=None, goal_info=None):
        """Evaluate every frame and transmit at most one 20 Hz command."""
        result = super().tick(
            frame_id, captured_at, processed_at, frame_width, frame_height,
            ball_info=ball_info, goal_info=goal_info)
        _, _, decision = result
        if self.finished:
            return result

        safe_relative = (
            decision.capability == LocalizationCapability.GOAL_RELATIVE and
            processed_at <= decision.valid_until)
        command = (decision.vx, decision.vy, decision.wz)
        if not safe_relative or command == (0, 0, 0):
            self._acquire_count = 0
            self._disarm("policy-zero")
            return result

        self._acquire_count += 1
        if self._acquire_count < self.acquire_cycles:
            return result
        if (self._last_send_at is not None and
                processed_at - self._last_send_at + 1e-12 <
                self.control_period):
            return result

        try:
            if not self.armed:
                self.link.arm()
                self.armed = True
            self.link.set_twist(*command)
            self.last_sent_vx, self.last_sent_vy, self.last_sent_wz = command
            self._last_send_at = processed_at
        except MotionLinkNotArmedError:
            # The STM32 timeout is a safe stop. Require fresh consecutive
            # observations before re-arming instead of retrying this command.
            self._acquire_count = 0
            self._disarm("host-not-armed")
        except Exception:
            self.stop("link-error")
            raise
        return result

    def _disarm(self, _reason):
        if self.armed:
            self.link.safe_stop()
        self.armed = False
        self.last_sent_vx = 0
        self.last_sent_vy = 0
        self.last_sent_wz = 0
        self._last_send_at = None

    def stop(self, reason):
        """Request STOP once and prevent later commands."""
        if self.finished:
            return
        self.finished = True
        self.stop_reason = reason
        self.link.safe_stop()
        self.armed = False
        self.last_sent_vx = 0
        self.last_sent_vy = 0
        self.last_sent_wz = 0

    def reset(self):
        self._disarm("reset")
        self._acquire_count = 0
        super().reset()
