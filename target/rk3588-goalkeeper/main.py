import cv2
import os
import time
from rknnpool import rknnPoolExecutor
from func import myFunc
from state_manager import StateManager, SystemState
from football_tracker import tracker
from motion_link import MotionLink, MotionLinkError

# ══════════════════════════════════════════════════════════════
# IMU 姿态传感器（MPU6050）
from mpu6050_imu import imu, get_pitch, get_roll, get_yaw
# ══════════════════════════════════════════════════════════════

# ── 摄像头参数 ───────────────────────────────────────────
CAMERA_ID = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS_TARGET = 120  # 120fps 摄像头，不限制帧率

# ── C5 HOST 串口（5 Pro UART7_M2，40-pin 待手册复核）─────
SERIAL_PORT = '/dev/ttyS7'
SERIAL_BAUD = 115200

# ── 模型参数 ─────────────────────────────────────────────
MODEL_PATH = "./rknnModel/model_26.7.25_i8.rknn"
TPEs = 6  # 推理线程数

# ── 初始化摄像头 ─────────────────────────────────────────
cap = cv2.VideoCapture(CAMERA_ID)
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
cap.set(cv2.CAP_PROP_FOURCC, fourcc)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)

# 验证实际参数
actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
actual_fps = cap.get(cv2.CAP_PROP_FPS)
actual_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
fourcc_str = "".join([chr((actual_fourcc >> 8 * i) & 0xFF) for i in range(4)])
print(f"摄像头: {actual_w}x{actual_h} @ {actual_fps:.0f}fps, 格式={fourcc_str}")

# ── 初始化推理池 ─────────────────────────────────────────
if not os.path.isfile(MODEL_PATH):
    print(f"模型文件不存在: {os.path.abspath(MODEL_PATH)}")
    print("请确认模型已放入 rknnModel/ 目录，且工作目录为仓库根目录")
    exit(-1)
pool = rknnPoolExecutor(rknnModel=MODEL_PATH, TPEs=TPEs, func=myFunc)

# ── 本地状态与 C5 运动链路 ───────────────────────────────
state_mgr = StateManager()
motion_link = None
try:
    motion_link = MotionLink(port=SERIAL_PORT, baudrate=SERIAL_BAUD)
    motion_link.open()
    link_status = motion_link.query()
    print(f"[C5] 已连接 {SERIAL_PORT}: mode={link_status.mode.name} "
          f"host={link_status.host_state.name} motion={link_status.motion_state.name}")
except (MotionLinkError, OSError, ValueError) as e:
    print(f"[C5] 运动链路不可用: {e}（本阶段继续视觉运行，不会自动运动）")
    if motion_link is not None:
        motion_link.close()
    motion_link = None

# ══════════════════════════════════════════════════════════════
# 启动 IMU 姿态传感器（后台线程，IDLE / INFERENCE 均持续运行）
try:
    imu.start()
except Exception as e:
    print(f"[IMU] 启动失败: {e}（程序将继续运行，姿态查询返回 None）")

# VOFA+ 调试不得复用 C5 运动串口；如需输出请使用独立 USB 串口。
# ══════════════════════════════════════════════════════════════

# ── 辅助函数 ─────────────────────────────────────────────
def prime_pool(cap, pool, count):
    """预热推理池：向池中塞入 count 帧，填满流水线"""
    for _ in range(count):
        ret, frame = cap.read()
        if not ret:
            return False
        pool.put(frame)
    return True


def drain_pool(pool):
    """排空推理池中残留的帧"""
    from queue import Empty
    while True:
        try:
            pool.queue.get_nowait()
        except Empty:
            break


def draw_status(img, state: SystemState, link):
    """在画面左上角显示当前状态"""
    color = (0, 255, 0) if state == SystemState.IDLE else (0, 0, 255)
    text = f"STATE: {state.value}"
    cv2.putText(img, text, (10, 35), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, color, 2, cv2.LINE_AA)
    # 按键提示
    cv2.putText(img, "Q=Quit | K=Toggle", (10, actual_h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    if link is not None and link.last_status is not None:
        status = link.last_status
        link_text = f"C5: {status.mode.name}/{status.host_state.name}/{status.motion_state.name}"
        cv2.putText(img, link_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 0), 1, cv2.LINE_AA)


# ── 初始预热（启动时默认 IDLE，但也预热好池以备切换） ────
if not cap.isOpened():
    print("无法打开摄像头")
    if motion_link is not None:
        motion_link.close()
    exit(-1)

# 预热推理池，这样切换到 INFERENCE 时可以立即开始
if not prime_pool(cap, pool, TPEs + 1):
    print("预热失败：无法读取足够帧")
    cap.release()
    pool.release()
    if motion_link is not None:
        motion_link.close()
    exit(-1)

print("系统就绪。默认状态: IDLE（按 K 键手动切换）")
print("本阶段不会自动 ARM 或根据检测结果发送运动指令")

# ── 主循环 ───────────────────────────────────────────────
prev_state = state_mgr.state   # 跟踪上一次状态，用于检测切换
transitioning = False           # 正在切换中
exit_code = 0                   # 0=正常退出(按Q)；1=异常退出(摄像头掉线等)，
                                # 非零时 systemd 的 Restart=on-failure 会自动重启
frames, loopTime, initTime = 0, time.time(), time.time()

try:
    while cap.isOpened():
        current_state = state_mgr.state
        state_changed = (current_state != prev_state)
        prev_state = current_state

        frames += 1
        ret, frame = cap.read()
        if not ret:
            print("摄像头读取失败，异常退出")
            exit_code = 1
            break

        if current_state == SystemState.INFERENCE:
            # ── 推理模式 ─────────────────────────────
            if state_changed:
                print("[切换] IDLE → INFERENCE，预热流水线...")
                drain_pool(pool)
                if not prime_pool(cap, pool, TPEs + 1):
                    print("预热失败：摄像头读取失败，异常退出")
                    exit_code = 1
                    break
                print("[切换] 预热完成，开始推理")
                loopTime = time.time()

            pool.put(frame)
            result, flag = pool.get()
            if not flag:
                print("推理池异常，退出")
                exit_code = 1
                break
            frame, boxes, classes, scores = result

            # Only publish detections; goalkeeper control is a later phase.
            football = tracker.update(boxes, classes, scores)
            if football is not None:
                x, y, conf = football
                cv2.drawMarker(frame, (x, y), (0, 255, 255),
                               cv2.MARKER_CROSS, 30, 2)
                cv2.putText(frame, f"FOOTBALL x={x} {conf:.2f}",
                            (x + 20, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 255), 2)

        elif state_changed:
            print("[切换] INFERENCE → IDLE，停止推理")
            drain_pool(pool)
            tracker.clear()
            if motion_link is not None:
                motion_link.safe_stop()
            loopTime = time.time()

        draw_status(frame, current_state, motion_link)
        cv2.imshow('yolov8', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('k'):
            if current_state == SystemState.IDLE:
                state_mgr.state = SystemState.INFERENCE
            else:
                state_mgr.state = SystemState.IDLE

        if frames % 30 == 0:
            label = f"[{current_state.value}]"
            print(f"{label} 30帧平均帧率:\t{30 / (time.time() - loopTime):.1f} 帧")
            loopTime = time.time()
            p, r, y = get_pitch(), get_roll(), get_yaw()
            if p is not None:
                print(f"         IMU:\tPitch={p:6.1f}°  Roll={r:6.1f}°  Yaw={y:6.1f}°")

    print("总平均帧率\t", frames / (time.time() - initTime))
finally:
    # Never leave an armed HOST session behind on normal or exceptional exit.
    if motion_link is not None:
        motion_link.safe_stop()
        motion_link.close()
    cap.release()
    cv2.destroyAllWindows()
    pool.release()
    imu.stop()

exit(exit_code)   # 异常退出码非零，配合 systemd Restart=on-failure 自动重启
