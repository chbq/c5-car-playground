"""Hardware-free adapter from detector boxes to goalkeeper decisions."""

from ball_follow_control import BallFollowConfig, BallFollowController
from goalkeeper_policy import (
    GoalkeeperPolicy,
    MotionIntent,
    PerceptionFrame,
    VisualObservation,
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

    def __init__(self, policy=None, candidate_controller=None, logger=None):
        self.policy = policy or GoalkeeperPolicy()
        self.candidate_controller = (
            candidate_controller or BallFollowController(BallFollowConfig()))
        self.logger = logger

    def tick(self, frame_id, captured_at, processed_at, frame_width,
             frame_height, ball_info=None, goal_info=None):
        ball = make_observation(ball_info, captured_at)
        goal = make_observation(goal_info, captured_at)
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
