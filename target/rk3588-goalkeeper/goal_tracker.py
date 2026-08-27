"""
球门共享状态跟踪器
- 主循环（main.py）每帧调用 goal_tracker.update() 写入最新球门检测结果；
  球门角点/顶宽由 goal_tracker.compute_geometry() 调用 PC 端 goal_geometry.process_goal 计算并缓存
- 其他任何模块/线程随时调用 get_goal_top_width()/get_goal_corners() 等读取（非阻塞）
- 当前帧没有球门、或数据超过 max_age 秒未更新（如系统处于 IDLE）时返回 None

用法:
    # 生产方（main.py 推理循环，每帧一次）:
    from goal_tracker import goal_tracker
    goal_tracker.update(boxes, classes, scores)
    goal_tracker.compute_geometry(clean_frame)   # 计算并缓存球门角点/顶宽

    # 消费方（任何模块/线程）:
    from goal_tracker import get_goal_info, get_goal_box, get_goal_top_width
    info = get_goal_info()        # -> GoalInfo 或 None
    box = get_goal_box()          # -> (x1, y1, x2, y2) float 或 None
    width = get_goal_top_width()  # -> TL↔TR 像素距离(float) 或 None
"""
import threading
import time
from collections import namedtuple

from func import get_goal_box as _extract_goal_box
from goal_geometry import process_goal

# 一次检测结果: x/y 为球门中心像素坐标, width/height 为检测框像素尺寸, conf 为置信度,
# ts 为写入时间(time.monotonic(), 单调时钟, 只用于计算数据年龄, 不是墙钟时间)
GoalInfo = namedtuple(
    "GoalInfo", ["x", "y", "width", "height", "conf", "ts"])

# 数据默认有效期（秒）: 超过该时长未更新视为过期，返回 None。
# 推理帧率 ≥ 30fps 时，0.5s 相当于连续约 15 帧没有新数据。
DEFAULT_MAX_AGE = 0.5

# PC 端 goal_football/main.py 已调参的球门几何参数（角点获取沿用 PC 代码）
GOAL_MASK_METHOD = "fused"
GOAL_CORNER_METHOD = "auto"
GOAL_ROI_MARGIN_SIDE = 0.05
GOAL_ROI_MARGIN_TOP = 0.15
GOAL_ROI_BOTTOM_FRAC = 0.2


class GoalTracker:
    """线程安全的球门状态缓存。

    写入方：main.py 每帧 update() 写入检测框；球门几何结果经 update_geometry() 写入。
    读取方：随时 get()/get_box()/get_corners()/get_top_width()，非阻塞。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._info = None       # GoalInfo 或 None
        self._box = None        # (x1, y1, x2, y2) float 或 None，供球门几何使用
        self._corners = None    # process_goal 结果 dict 或 None
        self._corners_ts = None  # 几何结果写入时间（time.monotonic()）

    def update(self, boxes, classes, scores):
        """用一帧检测结果刷新缓存。
        返回 (x, y, conf) 或 None，方便主循环直接用于画面标注。
        本帧没有球门时清空缓存（此后 get 立即返回 None）。
        """
        detection = _extract_goal_box(boxes, classes, scores)
        if detection is None:
            with self._lock:
                self._info = None
                self._box = None
                self._corners = None
                self._corners_ts = None
            return None
        x1, y1, x2, y2, conf = detection
        x = int((x1 + x2) / 2)
        y = int((y1 + y2) / 2)
        width = max(0, int(round(x2 - x1)))
        height = max(0, int(round(y2 - y1)))
        with self._lock:
            self._info = GoalInfo(x, y, width, height, conf, time.monotonic())
            self._box = (float(x1), float(y1), float(x2), float(y2))
        return x, y, conf

    def get(self, max_age=DEFAULT_MAX_AGE):
        """返回最新 GoalInfo（含中心、框尺寸和置信度）；无球门或过期返回 None。
        max_age=None 表示不做过期检查。
        """
        with self._lock:
            info = self._info
        if info is None:
            return None
        if max_age is not None and time.monotonic() - info.ts > max_age:
            return None
        return info

    def get_box(self, max_age=DEFAULT_MAX_AGE):
        """返回最新球门检测框 (x1, y1, x2, y2)（float）；无球门或过期返回 None。"""
        with self._lock:
            info = self._info
            box = self._box
        if info is None:
            return None
        if max_age is not None and time.monotonic() - info.ts > max_age:
            return None
        return box

    def update_geometry(self, corners):
        """缓存 process_goal 的几何结果（球门四角与顶宽）；corners 为 None 时清空。"""
        with self._lock:
            if corners is None:
                self._corners = None
                self._corners_ts = None
            else:
                self._corners = corners
                self._corners_ts = time.monotonic()

    def compute_geometry(self, frame, margin_side=GOAL_ROI_MARGIN_SIDE,
                         margin_top=GOAL_ROI_MARGIN_TOP,
                         roi_bottom_frac=GOAL_ROI_BOTTOM_FRAC,
                         method=GOAL_MASK_METHOD,
                         corner_method=GOAL_CORNER_METHOD):
        """用 PC 端 goal_geometry.process_goal 在给定帧上计算球门角点/顶宽，并缓存结果。

        frame 应为未标注的全分辨率干净帧；box 取当前缓存的球门检测框。
        返回 corners dict（含 TL/TR/BL/BR/top_width/source）或 None；
        当前没有球门框时清空几何缓存并返回 None。
        """
        box = self.get_box()
        if box is None:
            self.update_geometry(None)
            return None
        corners = process_goal(
            frame, box,
            margin_side=margin_side,
            margin_top=margin_top,
            roi_bottom_frac=roi_bottom_frac,
            method=method,
            corner_method=corner_method,
        )
        self.update_geometry(corners)
        return corners

    def get_corners(self, max_age=DEFAULT_MAX_AGE):
        """返回最新球门几何结果 dict（TL/TR/BL/BR/top_width/source）；无或过期返回 None。"""
        with self._lock:
            corners = self._corners
            ts = self._corners_ts
        if corners is None:
            return None
        if max_age is not None and time.monotonic() - ts > max_age:
            return None
        return corners

    def get_top_width(self, max_age=DEFAULT_MAX_AGE):
        """返回最新球门横梁顶宽（TL↔TR 欧氏像素距离, float）；无或过期返回 None。"""
        corners = self.get_corners(max_age)
        if corners is None:
            return None
        return corners.get("top_width")

    def get_x(self, max_age=DEFAULT_MAX_AGE):
        """返回最新球门 x 中心坐标(int)；无球门或数据过期返回 None。"""
        info = self.get(max_age)
        return info.x if info is not None else None

    def clear(self):
        """清空缓存（如切换到 IDLE 状态时调用）。"""
        with self._lock:
            self._info = None
            self._box = None
            self._corners = None
            self._corners_ts = None


# ── 模块级单例 + 便捷函数 ─────────────────────────────────
goal_tracker = GoalTracker()


def get_goal_x(max_age=DEFAULT_MAX_AGE):
    """获取最新球门 x 坐标（像素, int）；当前无球门或数据过期返回 None。"""
    return goal_tracker.get_x(max_age)


def get_goal_info(max_age=DEFAULT_MAX_AGE):
    """获取含中心、框尺寸和置信度的球门信息；无球门或过期返回 None。"""
    return goal_tracker.get(max_age)


def get_goal_box(max_age=DEFAULT_MAX_AGE):
    """获取最新球门检测框 (x1, y1, x2, y2)（float）；无球门或过期返回 None。"""
    return goal_tracker.get_box(max_age)


def get_goal_corners(max_age=DEFAULT_MAX_AGE):
    """获取最新球门几何结果（含 TL/TR/BL/BR/top_width/source）；无或过期返回 None。"""
    return goal_tracker.get_corners(max_age)


def get_goal_top_width(max_age=DEFAULT_MAX_AGE):
    """获取最新球门横梁顶宽（TL↔TR 像素距离, float）；无或过期返回 None。"""
    return goal_tracker.get_top_width(max_age)
