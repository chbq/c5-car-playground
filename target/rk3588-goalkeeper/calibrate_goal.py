"""标定工具：足球边长/面积、球门中心 x、球门横梁顶宽。

实时显示标定量（供填入 config.json）：

- football.length_side     足球上水平边长（检测框宽，像素）→ config.json 的 football.length_side
- football.area            足球面积（检测框宽×高，像素²）  → 定 football.area_near / area_far
- goal.target_x            球门中心 x（像素）             → config.json 的 goal.target_x
- goal.target_top_width    球门横梁顶宽（像素）           → config.json 的 goal.target_top_width

把足球/球门放到期望的距离/位置，读出对应值，填进 config.json 即可。

用法:
    python3 calibrate_goal.py              # 带窗口，实时叠加显示
    python3 calibrate_goal.py --headless   # 无窗口，打印到终端（SSH）

按 q 退出（带窗口时）。
"""
import argparse
import os
import time

import cv2

from football_tracker import tracker
from func import myFunc
from goal_tracker import goal_tracker
from rknnpool import rknnPoolExecutor


CAMERA_ID = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS_TARGET = 120

MODEL_PATH = "./rknnModel/football_8_16_100.rknn"
TPEs = 6

GEOMETRY_PERIOD = 0.2        # 几何计算节流（秒），约 5 Hz
HEADLESS_PRINT_PERIOD = 0.5  # headless 打印节流（秒），避免刷屏


def configure_camera():
    cap = cv2.VideoCapture(CAMERA_ID)
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS_TARGET)
    return cap


def prime_pool(cap, pool, count):
    """预热推理池：向池中塞入 count 帧，填满流水线。"""
    for _ in range(count):
        ok, frame = cap.read()
        if not ok:
            return False
        pool.put(frame)
    return True


def draw_overlay(frame, football_side, football_area, goal_x, top_width,
                 corners):
    """在帧上叠加标定信息：足球边长/面积、球门中心 x、球门顶宽。"""
    tl = corners.get("TL") if corners else None
    tr = corners.get("TR") if corners else None
    for point in (tl, tr):
        if point is not None:
            cv2.circle(frame, (int(point[0]), int(point[1])), 5, (0, 255, 0), 2)
    if tl is not None and tr is not None:
        cv2.line(frame, (int(tl[0]), int(tl[1])),
                 (int(tr[0]), int(tr[1])), (0, 255, 0), 2)

    line0 = (
        f"football side = {football_side}px"
        if football_side is not None else "football side = -")
    line1 = (
        f"football area = {football_area}px2"
        if football_area is not None else "football area = -")
    line2 = (
        f"goal center_x = {goal_x}"
        if goal_x is not None else "goal center_x = -")
    line3 = (
        f"goal top_width = {top_width:.1f}px"
        if top_width is not None else "goal top_width = -")
    for y, text in ((35, line0), (65, line1), (95, line2), (125, line3)):
        cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "Q=Quit | P=Print", (10, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)


def run(headless):
    if not os.path.isfile(MODEL_PATH):
        print(f"模型文件不存在: {os.path.abspath(MODEL_PATH)}")
        return 2

    cap = configure_camera()
    if not cap.isOpened():
        print("无法打开摄像头")
        return 2

    pool = rknnPoolExecutor(rknnModel=MODEL_PATH, TPEs=TPEs, func=myFunc)
    if not prime_pool(cap, pool, TPEs + 1):
        print("预热失败：无法读取足够帧")
        cap.release()
        pool.release()
        return 2
    print("标定开始：读出足球边长/面积、球门中心 x、球门顶宽。q=退出")

    geometry_last = 0.0
    print_last = 0.0
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                print("摄像头读取失败，退出")
                break

            pool.put(frame)
            result, ok = pool.get()
            if not ok:
                print("推理池异常，退出")
                break
            clean_frame, frame, boxes, classes, scores = result

            # 每帧刷新足球与球门检测框缓存
            tracker.update(boxes, classes, scores)
            goal_tracker.update(boxes, classes, scores)

            # 周期计算球门几何（顶宽），其余帧用缓存
            now = time.monotonic()
            if now - geometry_last >= GEOMETRY_PERIOD:
                geometry_last = now
                corners = goal_tracker.compute_geometry(clean_frame)
            else:
                corners = goal_tracker.get_corners()

            # 足球上水平边长 = 检测框宽；面积 = 宽 × 高
            football_info = tracker.get(max_age=None)
            if football_info is not None:
                football_side = football_info.width
                football_area = football_info.width * football_info.height
            else:
                football_side = None
                football_area = None
            goal_x = goal_tracker.get_x()
            top_width = goal_tracker.get_top_width()

            if headless:
                if now - print_last >= HEADLESS_PRINT_PERIOD:
                    print_last = now
                    side_text = (
                        "-" if football_side is None else f"{football_side}")
                    area_text = (
                        "-" if football_area is None else f"{football_area}")
                    width_text = (
                        "-" if top_width is None else f"{top_width:.1f}")
                    print(
                        f"[CAL] side={side_text}px area={area_text}px2 "
                        f"goal_x={goal_x} top_width={width_text}px")
            else:
                draw_overlay(frame, football_side, football_area,
                             goal_x, top_width, corners)
                cv2.imshow("calibration", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key == ord("p"):
                    side = "-" if football_side is None else str(football_side)
                    area = "-" if football_area is None else str(football_area)
                    gx = "-" if goal_x is None else str(goal_x)
                    width = "-" if top_width is None else f"{top_width:.1f}"
                    print(
                        f"[CAL] football.length_side={side} "
                        f"football.area={area} "
                        f"goal.target_x={gx} "
                        f"goal.target_top_width={width}")
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，退出")
    finally:
        tracker.clear()
        goal_tracker.clear()
        cap.release()
        pool.release()
        cv2.destroyAllWindows()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="标定：足球边长/面积、球门中心 x、球门顶宽")
    parser.add_argument(
        "--headless", action="store_true",
        help="无窗口，打印到终端（SSH 场景）")
    args = parser.parse_args()
    return run(args.headless)


if __name__ == "__main__":
    raise SystemExit(main())
