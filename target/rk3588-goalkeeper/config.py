"""目标值（setpoint）配置。

从 config.json 读取控制目标值，启动加载一次并缓存；改文件需重启服务。
三个目标值（单位均为像素，与 football_tracker / goal_tracker 的测量值一致）：

- football.target_x        足球中心 x 的目标像素坐标（默认 640 = 1280/2 画面中心）
- football.length_side     足球上水平边长（检测框宽）的目标像素值（默认 100，按实际距离调）
- football.area_near       足球面积近端阈值（像素²，超过视为足够近；默认 8000，按实际调）
- football.area_far        足球面积远端阈值（像素²，低于视为太远；默认 1500，按实际调）
- goal.target_x            球门中心 x 的目标像素坐标（默认 640）
- goal.target_top_width    球门横梁顶宽 TL↔TR 的目标像素距离（默认 150，按实际场地/距离调）

config.json 缺失、解析失败或字段缺失时回退到默认值，不抛异常。

用法:
    from config import get_football_target_x, get_goal_target_top_width
    target = get_football_target_x()      # -> int 像素坐标
    width  = get_goal_target_top_width()  # -> float 像素距离
"""
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

_DEFAULTS = {
    "football": {
        "target_x": 640, "length_side": 100,
        "area_near": 8000, "area_far": 1500,
    },
    "goal": {"target_x": 640, "target_top_width": 150.0},
}


def _coerce(value, cast):
    """安全类型转换；失败返回 None。"""
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def load_config(path=_CONFIG_PATH):
    """读取 config.json，返回合并默认值后的目标值 dict（容错，不抛异常）。"""
    data = {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        print(f"[config] 未找到 {path}，使用默认目标值")
    except json.JSONDecodeError as exc:
        print(f"[config] {path} 解析失败: {exc}，使用默认目标值")
    except OSError as exc:
        print(f"[config] 读取 {path} 失败: {exc}，使用默认目标值")

    if not isinstance(data, dict):
        print(f"[config] {path} 根节点应为对象，使用默认目标值")
        data = {}

    football = data.get("football")
    goal = data.get("goal")
    if not isinstance(football, dict):
        football = {}
    if not isinstance(goal, dict):
        goal = {}

    def pick(section, key, cast, default):
        value = _coerce(section.get(key), cast)
        return default if value is None else value

    return {
        "football": {
            "target_x": pick(
                football, "target_x", int,
                _DEFAULTS["football"]["target_x"]),
            "length_side": pick(
                football, "length_side", int,
                _DEFAULTS["football"]["length_side"]),
            "area_near": pick(
                football, "area_near", int,
                _DEFAULTS["football"]["area_near"]),
            "area_far": pick(
                football, "area_far", int,
                _DEFAULTS["football"]["area_far"]),
        },
        "goal": {
            "target_x": pick(
                goal, "target_x", int, _DEFAULTS["goal"]["target_x"]),
            "target_top_width": pick(
                goal, "target_top_width", float,
                _DEFAULTS["goal"]["target_top_width"]),
        },
    }


# 启动加载一次（模块导入时）
_targets = load_config()


def get_football_target_x():
    """足球中心 x 的目标像素坐标（int）。"""
    return _targets["football"]["target_x"]


def get_football_target_length_side():
    """足球上水平边长（检测框宽）的目标像素值（int）。"""
    return _targets["football"]["length_side"]


def get_football_target_area_near():
    """足球面积近端阈值（像素²，int）。"""
    return _targets["football"]["area_near"]


def get_football_target_area_far():
    """足球面积远端阈值（像素²，int）。"""
    return _targets["football"]["area_far"]


def get_goal_target_x():
    """球门中心 x 的目标像素坐标（int）。"""
    return _targets["goal"]["target_x"]


def get_goal_target_top_width():
    """球门横梁顶宽的目标像素距离（float）。"""
    return _targets["goal"]["target_top_width"]
