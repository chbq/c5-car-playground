"""
足球坐标共享状态跟踪器
- 主循环（main.py）每帧调用 tracker.update() 写入最新检测结果
- 其他任何模块/线程随时调用 get_football_x() 读取最新 x 坐标（非阻塞）
- 当前帧没有足球、或数据超过 max_age 秒未更新（如系统处于 IDLE）时返回 None

用法:
    # 生产方（main.py 推理循环，每帧一次）:
    from football_tracker import tracker
    football = tracker.update(boxes, classes, scores)

    # 消费方（任何模块/线程）:
    from football_tracker import get_football_x
    x = get_football_x()          # -> int 像素坐标, 或 None
"""
import threading
import time
from collections import namedtuple

from func import get_football as _extract_football

# 一次检测结果: x/y 为足球中心像素坐标, conf 为置信度,
# ts 为写入时间(time.monotonic(), 单调时钟, 只用于计算数据年龄, 不是墙钟时间)
FootballInfo = namedtuple("FootballInfo", ["x", "y", "conf", "ts"])

# 数据默认有效期（秒）: 超过该时长未更新视为过期，返回 None。
# 推理帧率 ≥ 30fps 时，0.5s 相当于连续约 15 帧没有新数据。
DEFAULT_MAX_AGE = 0.5


class FootballTracker:
    """线程安全的足球坐标缓存。写入方每帧 update()，读取方随时 get()/get_x()。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._info = None  # FootballInfo 或 None

    def update(self, boxes, classes, scores):
        """用一帧检测结果刷新缓存。
        返回 (x, y, conf) 或 None，方便主循环直接用于画面标注/串口发送。
        本帧没有足球时清空缓存（此后 get 立即返回 None）。
        """
        football = _extract_football(boxes, classes, scores)
        with self._lock:
            if football is None:
                self._info = None
            else:
                x, y, conf = football
                self._info = FootballInfo(x, y, conf, time.monotonic())
        return football

    def get(self, max_age=DEFAULT_MAX_AGE):
        """返回最新 FootballInfo(x, y, conf, ts)；无球或数据过期返回 None。
        max_age=None 表示不做过期检查。
        """
        with self._lock:
            info = self._info
        if info is None:
            return None
        if max_age is not None and time.monotonic() - info.ts > max_age:
            return None
        return info

    def get_x(self, max_age=DEFAULT_MAX_AGE):
        """返回最新足球 x 中心坐标(int)；无球或数据过期返回 None。"""
        info = self.get(max_age)
        return info.x if info is not None else None

    def clear(self):
        """清空缓存（如切换到 IDLE 状态时调用）。"""
        with self._lock:
            self._info = None


# ── 模块级单例 + 便捷函数 ─────────────────────────────────
tracker = FootballTracker()


def get_football_x(max_age=DEFAULT_MAX_AGE):
    """获取最新足球 x 坐标（像素, int）；当前无球或数据过期返回 None。"""
    return tracker.get_x(max_age)


def get_football_info(max_age=DEFAULT_MAX_AGE):
    """获取最新足球信息 FootballInfo(x, y, conf, ts)；无球或过期返回 None。"""
    return tracker.get(max_age)
