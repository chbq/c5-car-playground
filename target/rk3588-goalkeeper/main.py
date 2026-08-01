import argparse
import os
import time

import cv2

from control_log import ControlCsvLogger
from ball_follow_control import (
    BallFollowConfig,
    BallFollowController,
    BallFollowSession,
)
from ball_yaw_control import (
    BallYawConfig,
    BallYawController,
    BallYawSession,
)
from ball_strafe_control import (
    BallStrafeConfig,
    BallStrafeController,
    BallStrafeSession,
)
from football_tracker import tracker
from func import myFunc
from motion_link import MotionLink, MotionLinkError
from mpu6050_imu import imu, get_pitch, get_roll, get_yaw
from rknnpool import rknnPoolExecutor
from state_manager import StateManager, SystemState


# 摄像头参数
CAMERA_ID = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS_TARGET = 120

# C5 HOST uses the core-board CH340 over Orange Pi USB.
SERIAL_PORT = "auto"
SERIAL_BAUD = 115200

# 模型参数
MODEL_PATH = "./rknnModel/model_26.7.25_i8.rknn"
TPEs = 6

# Phase 5A yaw, 5B lateral, 5C camera follow and 5D FOV protection.
BALL_CONTROL_PERIOD = 0.05
BALL_ACQUIRE_CYCLES = 3
BALL_LOST_TIMEOUT = 0.5
BALL_TEST_MAX_DURATION = 30.0
BALL_MOTION_MODES = (
    "ball-yaw-test", "ball-strafe-test", "ball-follow-test",
    "ball-fov-test")
BALL_PROFILES = {
    "standard": {
        "duration": 10.0,
        "min_wz": 40,
        "max_wz": 100,
        "kp": 120.0,
        "deadband": 0.08,
        "min_confidence": 0.50,
        "lost_timeout": 0.5,
        "hold_arm_until_duration": False,
    },
    "ground-check": {
        "duration": 15.0,
        "min_wz": 60,
        "max_wz": 120,
        "kp": 150.0,
        "deadband": 0.12,
        "min_confidence": 0.35,
        "lost_timeout": 1.5,
        "hold_arm_until_duration": True,
    },
    "ground-demo": {
        "duration": 30.0,
        "min_wz": 70,
        "max_wz": 160,
        "kp": 200.0,
        "deadband": 0.12,
        "min_confidence": 0.35,
        "lost_timeout": 1.5,
        "hold_arm_until_duration": True,
    },
}
BALL_STRAFE_DEFAULTS = {
    "duration": 30.0,
    "min_vy": 250,
    "max_vy": 800,
    "lateral_kp": 1000.0,
    "lateral_deadband": 0.10,
    "max_vy_step": 120,
    "lateral_sign": -1,
    "min_confidence": 0.35,
    "lost_timeout": 1.5,
    "hold_arm_until_duration": True,
}
BALL_FOLLOW_DEFAULTS = {
    "duration": 30.0,
    "min_vx": 250,
    "max_vx": 800,
    "max_vx_step": 120,
    "vx_kp": 1000.0,
    "vx_sign": -1,
    "min_vy": 200,
    "max_vy": 600,
    "max_vy_step": 100,
    "distance_kp": 4000.0,
    "distance_deadband": 0.05,
    "target_box_ratio": 0.35,
    "vy_sign": 1,
    "min_wz": 40,
    "max_wz": 180,
    "kp": 220.0,
    "deadband": 0.10,
    "yaw_sign": 1,
    "min_confidence": 0.35,
    "lost_timeout": 1.5,
    "hold_arm_until_duration": True,
}
BALL_FOV_DEFAULTS = {
    "duration": 30.0,
    "min_vx": 250,
    "max_vx": 800,
    "max_vx_step": 120,
    "vx_kp": 1000.0,
    "vx_sign": -1,
    "min_vy": 200,
    "max_vy": 600,
    "max_vy_step": 100,
    "distance_kp": 4000.0,
    "distance_deadband": 0.05,
    "target_box_ratio": 0.35,
    "vy_sign": 1,
    "min_wz": 60,
    "max_wz": 260,
    "kp": 320.0,
    "deadband": 0.10,
    "yaw_sign": 1,
    "min_confidence": 0.35,
    "lost_timeout": 1.5,
    "hold_arm_until_duration": True,
    "fov_error_alpha": 0.55,
    "fov_rate_alpha": 0.35,
    "fov_prediction_horizon": 0.15,
    "fov_predict_hold": 0.15,
    "fov_edge_enter": 0.55,
    "fov_edge_exit": 0.30,
    "fov_translation_scale": 0.25,
}


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="RK3588 football inference and bounded C5 motion tests")
    parser.add_argument(
        "--mode", choices=("idle", "inference") + BALL_MOTION_MODES,
        default="idle",
        help="idle/inference never move; ball tests are dry-run unless --execute")
    parser.add_argument(
        "--headless", action="store_true",
        help="disable the OpenCV window for SSH operation")
    parser.add_argument(
        "--profile", choices=tuple(BALL_PROFILES), default="standard",
        help="repeatable ball-yaw parameter preset")
    parser.add_argument(
        "--execute", action="store_true",
        help="explicitly ARM and send bounded motion in a ball test mode")
    parser.add_argument(
        "--duration", type=float,
        help="ball motion test duration in seconds (1..30)")
    parser.add_argument("--max-wz", type=int)
    parser.add_argument("--min-wz", type=int)
    parser.add_argument("--kp", type=float)
    parser.add_argument("--deadband", type=float)
    parser.add_argument("--min-confidence", type=float)
    parser.add_argument(
        "--lost-timeout", type=float,
        help="seconds before STOP after target loss (0.5..2.0)")
    parser.add_argument(
        "--hold-arm-until-duration", action="store_true",
        help="raised test only: target loss sends zero without early disarm")
    parser.add_argument(
        "--yaw-sign", type=int, choices=(-1, 1), default=1,
        help="+1: ball on image right requests clockwise wz")
    parser.add_argument("--max-vy", type=int)
    parser.add_argument("--min-vy", type=int)
    parser.add_argument("--lateral-kp", type=float)
    parser.add_argument("--lateral-deadband", type=float)
    parser.add_argument("--max-vy-step", type=int)
    parser.add_argument(
        "--lateral-sign", type=int, choices=(-1, 1),
        help="+1: ball on image right requests positive/right vy")
    parser.add_argument("--max-vx", type=int)
    parser.add_argument("--min-vx", type=int)
    parser.add_argument("--max-vx-step", type=int)
    parser.add_argument("--vx-kp", type=float)
    parser.add_argument(
        "--vx-sign", type=int, choices=(-1, 1),
        help="-1: image-right ball requests negative vx")
    parser.add_argument("--distance-kp", type=float)
    parser.add_argument("--distance-deadband", type=float)
    parser.add_argument("--target-box-ratio", type=float)
    parser.add_argument(
        "--vy-sign", type=int, choices=(-1, 1),
        help="+1: a distant ball requests positive camera-forward vy")
    parser.add_argument(
        "--control-log",
        help="Phase 5C/5D CSV path; default logs/<mode>-<time>.csv")
    parser.add_argument("--fov-error-alpha", type=float)
    parser.add_argument("--fov-rate-alpha", type=float)
    parser.add_argument("--fov-prediction-horizon", type=float)
    parser.add_argument("--fov-predict-hold", type=float)
    parser.add_argument("--fov-edge-enter", type=float)
    parser.add_argument("--fov-edge-exit", type=float)
    parser.add_argument("--fov-translation-scale", type=float)
    return parser


def parse_args(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    explicit_hold = args.hold_arm_until_duration
    fov_argument_names = (
        "fov_error_alpha", "fov_rate_alpha", "fov_prediction_horizon",
        "fov_predict_hold", "fov_edge_enter", "fov_edge_exit",
        "fov_translation_scale")
    explicit_fov = any(
        getattr(args, name) is not None for name in fov_argument_names)
    if args.mode == "ball-strafe-test":
        if args.profile != "standard":
            parser.error("yaw profiles are not valid with ball-strafe-test")
        defaults = BALL_STRAFE_DEFAULTS
    elif args.mode in ("ball-follow-test", "ball-fov-test"):
        if args.profile != "standard":
            parser.error("yaw profiles are not valid with ball follow modes")
        defaults = (
            BALL_FOV_DEFAULTS if args.mode == "ball-fov-test"
            else BALL_FOLLOW_DEFAULTS)
    else:
        defaults = BALL_PROFILES[args.profile]

    for name, value in defaults.items():
        if name == "hold_arm_until_duration":
            if value and args.execute:
                args.hold_arm_until_duration = True
        elif getattr(args, name) is None:
            setattr(args, name, value)

    if args.execute and args.mode not in BALL_MOTION_MODES:
        parser.error("--execute is only valid with a ball motion test mode")
    if (args.control_log and
            args.mode not in ("ball-follow-test", "ball-fov-test")):
        parser.error("--control-log requires a ball follow mode")
    if explicit_fov and args.mode != "ball-fov-test":
        parser.error("FOV parameters require --mode ball-fov-test")
    if explicit_hold and not args.execute:
        parser.error("--hold-arm-until-duration requires --execute")
    if args.mode in BALL_MOTION_MODES:
        if not 1.0 <= args.duration <= BALL_TEST_MAX_DURATION:
            parser.error("--duration must be in [1, 30] for ball motion tests")
    elif args.profile != "standard":
        parser.error("ground profiles require --mode ball-yaw-test")
    if args.headless and args.mode == "idle":
        parser.error("--headless requires inference or a ball motion test")
    if not 0.5 <= args.lost_timeout <= 2.0:
        parser.error("--lost-timeout must be in [0.5, 2.0]")

    try:
        if args.mode in ("ball-follow-test", "ball-fov-test"):
            make_ball_follow_config(args).validate()
        elif args.mode == "ball-strafe-test":
            BallStrafeConfig(
                deadband=args.lateral_deadband,
                min_confidence=args.min_confidence,
                proportional_gain=args.lateral_kp,
                min_vy=args.min_vy,
                max_vy=args.max_vy,
                max_step=args.max_vy_step,
                lateral_sign=args.lateral_sign,
            ).validate()
        else:
            BallYawConfig(
                deadband=args.deadband,
                min_confidence=args.min_confidence,
                proportional_gain=args.kp,
                min_wz=args.min_wz,
                max_wz=args.max_wz,
                yaw_sign=args.yaw_sign,
            ).validate()
    except ValueError as error:
        parser.error(str(error))
    return args


def configure_camera():
    cap = cv2.VideoCapture(CAMERA_ID)
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)
    return cap


def camera_description(cap):
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_text = "".join(
        chr((fourcc >> 8 * index) & 0xFF) for index in range(4))
    return width, height, fps, fourcc_text


def prime_pool(cap, pool, count):
    """预热推理池：向池中塞入 count 帧，填满流水线。"""
    for _ in range(count):
        ok, frame = cap.read()
        if not ok:
            return False
        pool.put(frame)
    return True


def drain_pool(pool):
    """排空推理池中残留的帧。"""
    from queue import Empty

    while True:
        try:
            pool.queue.get_nowait()
        except Empty:
            break


def draw_status(image, state, link, decision):
    """显示运行状态、HOST 状态和最近一次像素控制结果。"""
    color = (0, 255, 0) if state == SystemState.IDLE else (0, 0, 255)
    cv2.putText(
        image, f"STATE: {state.value}", (10, 35),
        cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)
    cv2.putText(
        image, "Q=Quit | K=Toggle", (10, image.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    if link is not None and link.last_status is not None:
        status = link.last_status
        text = (
            f"C5: {status.mode.name}/{status.host_state.name}/"
            f"{status.motion_state.name}")
        cv2.putText(
            image, text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (255, 255, 0), 1, cv2.LINE_AA)

    if decision is not None:
        if (hasattr(decision, "vx") and hasattr(decision, "vy") and
                hasattr(decision, "wz")):
            command_text = (
                f"vx={decision.vx:+d} vy={decision.vy:+d} "
                f"wz={decision.wz:+d}")
        elif hasattr(decision, "vy") and hasattr(decision, "wz"):
            command_text = f"vy={decision.vy:+d} wz={decision.wz:+d}"
        elif hasattr(decision, "vy"):
            command_text = f"vy={decision.vy:+d}"
        else:
            command_text = f"wz={decision.wz:+d}"
        text = (
            f"BALL: {decision.state.value} "
            f"error={decision.error:+.3f} {command_text}")
        zone = getattr(decision, "zone", None)
        if zone is not None and zone.value != "OFF":
            text += f" zone={zone.value}"
        cv2.putText(
            image, text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX,
            0.55, (0, 255, 255), 1, cv2.LINE_AA)


def print_decision(decision, session):
    confidence = (
        "-" if decision.confidence is None else f"{decision.confidence:.2f}")
    x = "-" if decision.x is None else str(decision.x)
    mode = "EXECUTE" if session.execute else "DRY"
    if (hasattr(decision, "vx") and hasattr(decision, "vy") and
            hasattr(decision, "wz")):
        target_text = (
            f"vx={decision.vx:+d} vy={decision.vy:+d} "
            f"wz={decision.wz:+d}")
        if session.last_sent_vx is None:
            sent_text = "-"
        else:
            sent_text = (
                f"vx={session.last_sent_vx:+d} "
                f"vy={session.last_sent_vy:+d} "
                f"wz={session.last_sent_wz:+d}")
    elif hasattr(decision, "vy") and hasattr(decision, "wz"):
        target_text = f"vy={decision.vy:+d} wz={decision.wz:+d}"
        if session.last_sent_vy is None:
            sent_text = "-"
        else:
            sent_text = (
                f"vy={session.last_sent_vy:+d} "
                f"wz={session.last_sent_wz:+d}")
    elif hasattr(decision, "vy"):
        target_text = f"vy={decision.vy:+d}"
        sent_text = (
            "-" if session.last_sent_vy is None
            else f"{session.last_sent_vy:+d}")
    else:
        target_text = f"wz={decision.wz:+d}"
        sent_text = (
            "-" if session.last_sent_wz is None
            else f"{session.last_sent_wz:+d}")
    box_text = ""
    if hasattr(decision, "box_ratio"):
        box_text = (
            f" box={decision.box_ratio:.3f} "
            f"distance_error={decision.distance_error:+.3f}")
    zone = getattr(decision, "zone", None)
    if zone is not None and zone.value != "OFF":
        box_text += (
            f" zone={zone.value} filtered={decision.filtered_error:+.3f} "
            f"rate={decision.error_rate:+.2f}/s "
            f"predicted={decision.predicted_error:+.3f} "
            f"age={decision.target_age:.3f}s lost={decision.lost_frames}")
    print(
        f"[BALL/{mode}] {decision.state.value:<14} x={x:<4} "
        f"conf={confidence:<4} error={decision.error:+.3f}{box_text} "
        f"target=({target_text}) sent=({sent_text}) "
        f"armed={session.armed} paused={session.paused}")


def open_motion_link():
    link = MotionLink(port=SERIAL_PORT, baudrate=SERIAL_BAUD)
    link.open()
    status = link.query()
    print(
        f"[C5] 已连接 {link.resolved_port}: mode={status.mode.name} "
        f"host={status.host_state.name} motion={status.motion_state.name}")
    return link


def make_ball_yaw_session(args, motion_link):
    config = BallYawConfig(
        deadband=args.deadband,
        min_confidence=args.min_confidence,
        proportional_gain=args.kp,
        min_wz=args.min_wz,
        max_wz=args.max_wz,
        yaw_sign=args.yaw_sign,
    )
    return BallYawSession(
        BallYawController(config),
        link=motion_link,
        execute=args.execute,
        control_period=BALL_CONTROL_PERIOD,
        acquire_cycles=BALL_ACQUIRE_CYCLES,
        lost_timeout=args.lost_timeout,
        hold_arm_until_duration=args.hold_arm_until_duration,
    )


def make_ball_strafe_session(args, motion_link):
    config = BallStrafeConfig(
        deadband=args.lateral_deadband,
        min_confidence=args.min_confidence,
        proportional_gain=args.lateral_kp,
        min_vy=args.min_vy,
        max_vy=args.max_vy,
        max_step=args.max_vy_step,
        lateral_sign=args.lateral_sign,
    )
    return BallStrafeSession(
        BallStrafeController(config),
        link=motion_link,
        execute=args.execute,
        control_period=BALL_CONTROL_PERIOD,
        acquire_cycles=BALL_ACQUIRE_CYCLES,
        lost_timeout=args.lost_timeout,
        hold_arm_until_duration=args.hold_arm_until_duration,
    )


def make_ball_follow_config(args):
    values = dict(
        deadband=args.deadband,
        min_confidence=args.min_confidence,
        vx_gain=args.vx_kp,
        min_vx=args.min_vx,
        max_vx=args.max_vx,
        max_vx_step=args.max_vx_step,
        vx_sign=args.vx_sign,
        target_box_ratio=args.target_box_ratio,
        distance_deadband=args.distance_deadband,
        vy_gain=args.distance_kp,
        min_vy=args.min_vy,
        max_vy=args.max_vy,
        max_vy_step=args.max_vy_step,
        vy_sign=args.vy_sign,
        yaw_gain=args.kp,
        min_wz=args.min_wz,
        max_wz=args.max_wz,
        yaw_sign=args.yaw_sign,
    )
    if args.mode == "ball-fov-test":
        values.update(
            fov_enabled=True,
            fov_error_alpha=args.fov_error_alpha,
            fov_rate_alpha=args.fov_rate_alpha,
            fov_prediction_horizon=args.fov_prediction_horizon,
            fov_predict_hold=args.fov_predict_hold,
            fov_edge_enter=args.fov_edge_enter,
            fov_edge_exit=args.fov_edge_exit,
            fov_translation_scale=args.fov_translation_scale,
        )
    return BallFollowConfig(**values)


def make_ball_follow_session(args, motion_link):
    config = make_ball_follow_config(args)
    return BallFollowSession(
        BallFollowController(config),
        link=motion_link,
        execute=args.execute,
        control_period=BALL_CONTROL_PERIOD,
        acquire_cycles=BALL_ACQUIRE_CYCLES,
        lost_timeout=args.lost_timeout,
        hold_arm_until_duration=args.hold_arm_until_duration,
    )


def run(args):
    cap = None
    pool = None
    motion_link = None
    ball_session = None
    control_logger = None
    imu_started = False
    exit_code = 0

    try:
        if not os.path.isfile(MODEL_PATH):
            print(f"模型文件不存在: {os.path.abspath(MODEL_PATH)}")
            print("请确认模型已放入 rknnModel/，并从上位机工程目录运行")
            return 2

        cap = configure_camera()
        if not cap.isOpened():
            print("无法打开摄像头")
            return 2
        actual_w, actual_h, actual_fps, fourcc = camera_description(cap)
        print(f"摄像头: {actual_w}x{actual_h} @ {actual_fps:.0f}fps, 格式={fourcc}")

        pool = rknnPoolExecutor(rknnModel=MODEL_PATH, TPEs=TPEs, func=myFunc)

        try:
            motion_link = open_motion_link()
        except (MotionLinkError, OSError, ValueError) as error:
            print(f"[C5] 运动链路不可用: {error}")
            if motion_link is not None:
                motion_link.close()
            motion_link = None
            if args.execute:
                print("[C5] --execute 要求可用的 HOST 链路，测试取消")
                return 2
            print("[C5] 继续视觉/干运行，不会自动运动")

        try:
            imu.start()
            imu_started = True
        except Exception as error:
            print(f"[IMU] 启动失败: {error}（继续运行）")

        if not prime_pool(cap, pool, TPEs + 1):
            print("预热失败：无法读取足够帧")
            return 2

        state_mgr = StateManager()
        if args.mode != "idle":
            state_mgr.state = SystemState.INFERENCE
        if args.mode == "ball-yaw-test":
            ball_session = make_ball_yaw_session(args, motion_link)
            action = "允许低速 wz" if args.execute else "只打印，不 ARM"
            print(
                f"[BALL] Phase 5A {action}；duration={args.duration:.1f}s "
                f"profile={args.profile} "
                f"wz=[-{args.max_wz},{args.max_wz}] "
                f"lost={args.lost_timeout:.1f}s "
                f"hold_arm={args.hold_arm_until_duration} "
                f"yaw_sign={args.yaw_sign:+d}")
        elif args.mode == "ball-strafe-test":
            ball_session = make_ball_strafe_session(args, motion_link)
            action = "允许横移 vy" if args.execute else "只打印，不 ARM"
            print(
                f"[BALL] Phase 5B {action}；duration={args.duration:.1f}s "
                f"vy=[-{args.max_vy},{args.max_vy}] "
                f"min_vy={args.min_vy} kp={args.lateral_kp:.0f} "
                f"deadband={args.lateral_deadband:.2f} "
                f"step={args.max_vy_step} "
                f"lost={args.lost_timeout:.1f}s "
                f"hold_arm={args.hold_arm_until_duration} "
                f"lateral_sign={args.lateral_sign:+d}")
        elif args.mode in ("ball-follow-test", "ball-fov-test"):
            ball_session = make_ball_follow_session(args, motion_link)
            phase = "5D" if args.mode == "ball-fov-test" else "5C"
            log_prefix = "ball-fov" if args.mode == "ball-fov-test" else "ball-follow"
            control_log_path = args.control_log or os.path.join(
                "logs", time.strftime(f"{log_prefix}-%Y%m%d-%H%M%S.csv"))
            control_logger = ControlCsvLogger(
                control_log_path, mode=args.mode)
            action = "允许 vx+vy+wz" if args.execute else "只打印，不 ARM"
            print(
                f"[BALL] Phase {phase} {action}；duration={args.duration:.1f}s "
                f"vx=[-{args.max_vx},{args.max_vx}] "
                f"vy=[-{args.max_vy},{args.max_vy}] "
                f"wz=[-{args.max_wz},{args.max_wz}] "
                f"vx_kp={args.vx_kp:.0f} "
                f"target_box={args.target_box_ratio:.2f} "
                f"distance_deadband={args.distance_deadband:.2f} "
                f"deadband={args.deadband:.2f} "
                f"lost={args.lost_timeout:.1f}s "
                f"hold_arm={args.hold_arm_until_duration} "
                f"vx_sign={args.vx_sign:+d} "
                f"vy_sign={args.vy_sign:+d} "
                f"yaw_sign={args.yaw_sign:+d}")
            if args.mode == "ball-fov-test":
                print(
                    f"[BALL] FOV edge={args.fov_edge_enter:.2f}/"
                    f"{args.fov_edge_exit:.2f} "
                    f"predict={args.fov_prediction_horizon:.2f}s "
                    f"hold={args.fov_predict_hold:.2f}s "
                    f"translation={args.fov_translation_scale:.2f}")
            print(f"[BALL] 逐周期 CSV: {control_logger.path}")
        else:
            print("系统就绪；推理模式不根据检测结果发送运动指令")

        prev_state = state_mgr.state
        frames = 0
        loop_time = time.monotonic()
        init_time = loop_time
        test_start = loop_time
        last_decision = None
        last_decision_log = 0.0
        last_decision_state = None

        while cap.isOpened():
            now = time.monotonic()
            if (ball_session is not None and
                    now - test_start >= args.duration):
                ball_session.stop("duration")
                print("[BALL] 达到测试时限，已 STOP")
                break

            current_state = state_mgr.state
            state_changed = current_state != prev_state
            prev_state = current_state

            frames += 1
            ok, frame = cap.read()
            if not ok:
                print("摄像头读取失败，异常退出")
                exit_code = 1
                break

            if current_state == SystemState.INFERENCE:
                if state_changed:
                    print("[切换] IDLE → INFERENCE，预热流水线...")
                    drain_pool(pool)
                    if not prime_pool(cap, pool, TPEs + 1):
                        print("预热失败：摄像头读取失败")
                        exit_code = 1
                        break
                    print("[切换] 预热完成，开始推理")
                    loop_time = time.monotonic()

                pool.put(frame)
                result, ok = pool.get()
                if not ok:
                    print("推理池异常，退出")
                    exit_code = 1
                    break
                frame, boxes, classes, scores = result

                football = tracker.update(boxes, classes, scores)
                if football is not None:
                    x, y, confidence = football
                    cv2.drawMarker(
                        frame, (x, y), (0, 255, 255),
                        cv2.MARKER_CROSS, 30, 2)
                    cv2.putText(
                        frame, f"FOOTBALL x={x} {confidence:.2f}",
                        (x + 20, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 255), 2)

                if ball_session is not None:
                    observation = tracker.get(max_age=None)
                    decision_now = time.monotonic()
                    if args.mode in ("ball-follow-test", "ball-fov-test"):
                        decision = ball_session.tick(
                            observation, frame.shape[1], frame.shape[0],
                            now=decision_now)
                    else:
                        decision = ball_session.tick(
                            observation, frame.shape[1], now=decision_now)
                    if decision is not None:
                        if control_logger is not None:
                            pitch = get_pitch() if imu_started else None
                            roll = get_roll() if imu_started else None
                            yaw = get_yaw() if imu_started else None
                            control_logger.write(
                                decision_now, observation, decision, ball_session,
                                pitch=pitch, roll=roll, yaw=yaw)
                        last_decision = decision
                        log_now = time.monotonic()
                        if (decision.state != last_decision_state or
                                log_now - last_decision_log >= 0.25):
                            print_decision(decision, ball_session)
                            last_decision_state = decision.state
                            last_decision_log = log_now
                    if ball_session.finished:
                        print(f"[BALL] 会话结束: {ball_session.stop_reason}")
                        break

            elif state_changed:
                print("[切换] INFERENCE → IDLE，停止推理")
                drain_pool(pool)
                tracker.clear()
                if motion_link is not None:
                    motion_link.safe_stop()
                loop_time = time.monotonic()

            if not args.headless:
                draw_status(frame, current_state, motion_link, last_decision)
                cv2.imshow("yolov8", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("k") and ball_session is None:
                    if current_state == SystemState.IDLE:
                        state_mgr.state = SystemState.INFERENCE
                    else:
                        state_mgr.state = SystemState.IDLE

            if frames % 30 == 0:
                elapsed = time.monotonic() - loop_time
                print(f"[{current_state.value}] 30帧平均帧率: {30 / elapsed:.1f}")
                loop_time = time.monotonic()
                pitch, roll, yaw = get_pitch(), get_roll(), get_yaw()
                if pitch is not None:
                    print(
                        f"         IMU: Pitch={pitch:6.1f}° "
                        f"Roll={roll:6.1f}° Yaw={yaw:6.1f}°")

        elapsed = max(time.monotonic() - init_time, 1e-9)
        print(f"总平均帧率: {frames / elapsed:.1f}")
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，停止")
    except (MotionLinkError, OSError, ValueError) as error:
        print(f"[BALL] 控制链路异常: {error}")
        exit_code = 1
    finally:
        tracker.clear()
        if ball_session is not None:
            ball_session.stop("exit")
        if control_logger is not None:
            control_logger.close()
        if (motion_link is not None and
                (ball_session is None or not ball_session.execute)):
            motion_link.safe_stop()
        if motion_link is not None:
            motion_link.close()
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        if pool is not None:
            pool.release()
        if imu_started:
            imu.stop()
    return exit_code


def main(argv=None):
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
