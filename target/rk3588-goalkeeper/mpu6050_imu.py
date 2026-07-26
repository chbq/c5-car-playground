"""
MPU6050 姿态解算接口（Mahony 互补滤波器）
- 后台线程持续读取 MPU6050 + 运行 Mahony 滤波器
- 提供线程安全的姿态查询接口（和 football_tracker 一样的共享状态模式）
- 不带串口输出，不占用 /dev/ttyS0

用法:
    from mpu6050_imu import imu, get_pitch, get_roll, get_yaw, get_attitude

    imu.start()          # 后台启动：校准 → 持续解算（启动约需 2s）
    pitch = get_pitch()  # 随时查询，返回 float(°) 或 None（尚未就绪）
    roll  = get_roll()
    yaw   = get_yaw()    # 注意：6 轴 IMU 无磁力计，yaw 会随时间漂移
    imu.stop()           # 清理

依赖: pip install smbus2
"""
import math
import threading
import time
from collections import namedtuple

Attitude = namedtuple("Attitude", ["pitch", "roll", "yaw", "ts"])

DEFAULT_BUS = 5            # I2C-5（RK3588 的 I2C 总线号）
DEFAULT_ADDR = 0x68        # MPU6050 默认地址
DEFAULT_KP = 2.0           # Mahony 加速度修正力度
DEFAULT_KI = 0.01          # Mahony 积分修正力度
CALIB_SAMPLES = 200        # 校准采样数


def _read_word(bus, addr, reg):
    """I2C 读取 16 位有符号值（MPU6050 大端字节序）。"""
    high = bus.read_byte_data(addr, reg)
    low = bus.read_byte_data(addr, reg + 1)
    value = (high << 8) | low
    if value >= 0x8000:
        value -= 65536
    return value


def _normalize(*args):
    """向量归一化（返回 tuple）。"""
    s = sum(x * x for x in args)
    if s < 1e-12:
        return args
    inv = 1.0 / math.sqrt(s)
    return tuple(x * inv for x in args)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


class MPU6050Imu:
    """MPU6050 + Mahony 滤波器姿态解算器。

    后台线程：校准 → 循环读取传感器 → Mahony 更新 → 写入共享状态。
    主线程：调用 get_pitch/roll/yaw/get_attitude 随时读取最新值。
    """

    def __init__(self, bus_id=DEFAULT_BUS, addr=DEFAULT_ADDR,
                 kp=DEFAULT_KP, ki=DEFAULT_KI):
        self._bus_id = bus_id
        self._addr = addr
        self._kp = kp
        self._ki = ki
        self._lock = threading.Lock()
        self._attitude = None  # Attitude 或 None（未就绪）
        self._running = False
        self._thread = None
        self._ready = threading.Event()  # 校准完成 + 第一帧解算成功
        self._vofa_writer = None         # VOFA+ 数据发送回调: bytes -> None

    # ── 状态查询（线程安全）──────────────────────────────

    def is_ready(self):
        """是否已完成校准，开始输出有效数据。"""
        return self._ready.is_set()

    def get_attitude(self):
        """返回最新 Attitude(pitch, roll, yaw, ts)；未就绪时返回 None。"""
        with self._lock:
            return self._attitude

    def get_pitch(self):
        a = self.get_attitude()
        return a.pitch if a else None

    def get_roll(self):
        a = self.get_attitude()
        return a.roll if a else None

    def get_yaw(self):
        a = self.get_attitude()
        return a.yaw if a else None

    # ── VOFA+ 串口输出（可选）──────────────────────────

    def enable_serial_vofa(self, port=None, baudrate=115200, writer=None):
        """开启 VOFA+ 串口输出——每帧发送 CSV 姿态数据供 VOFA+ 实时绘图。

        两种用法:

        1. 使用调用方提供的独立 writer:
           imu.enable_serial_vofa(writer=debug_port.write)
           writer 不得绑定 C5 HOST 运动串口。

        2. 独立串口:
           imu.enable_serial_vofa(port='/dev/ttyUSB0', baudrate=115200)
           打开独立串口。注意不要和 STM32 MotionLink 使用同一个口。

        数据格式（10列, 逗号分隔, \\\\n 结尾）:
          pitch,roll,yaw,ax,ay,az,gx,gy,gz,temp
        """
        self.disable_serial_vofa()
        if writer is not None:
            self._vofa_writer = writer
            print("[MPU6050-VOFA] 已开启（复用已有串口）")
        elif port is not None:
            try:
                import serial
            except ImportError:
                print("[MPU6050-VOFA] pyserial 未安装。安装: pip install pyserial")
                return
            try:
                ser = serial.Serial(port, baudrate, timeout=0.1)
                self._vofa_writer = ser.write
                print(f"[MPU6050-VOFA] 串口已打开: {port} @ {baudrate}")
            except Exception as e:
                print(f"[MPU6050-VOFA] 打开 {port} 失败: {e}")
        else:
            print("[MPU6050-VOFA] 请指定 port= 或 writer=")

    def disable_serial_vofa(self):
        """关闭 VOFA+ 串口输出。"""
        old = self._vofa_writer
        self._vofa_writer = None
        # 如果是独立打开的串口（writer 绑定到 serial.write），关掉它
        if old is not None and hasattr(old, '__self__'):
            try:
                old.__self__.close()
                print("[MPU6050-VOFA] 串口已关闭")
            except Exception:
                pass

    # ── 生命周期 ───────────────────────────────────────

    def start(self):
        """启动后台姿态解算线程（非阻塞）。"""
        if self._running:
            return
        self._running = True
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止后台线程，关闭 I2C。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    # ── 后台线程 ───────────────────────────────────────

    def _run(self):
        bus = None
        try:
            # ── 导入 + I2C 初始化 ──────────────────
            try:
                import smbus2
            except ImportError:
                print("[MPU6050] smbus2 未安装。安装: pip install smbus2")
                return
            try:
                bus = smbus2.SMBus(self._bus_id)
                bus.write_byte_data(self._addr, 0x6B, 0x00)  # 唤醒 MPU6050
            except Exception as e:
                print(f"[MPU6050] I2C-{self._bus_id} 打开失败: {e}")
                return
            # ── 校准 ─────────────────────────────────
            print("[MPU6050] 校准中，请保持静止...")
            gbx, gby, gbz = 0.0, 0.0, 0.0
            ok = 0
            for _ in range(CALIB_SAMPLES):
                try:
                    gbx += _read_word(bus, self._addr, 0x43) / 131.0
                    gby += _read_word(bus, self._addr, 0x45) / 131.0
                    gbz += _read_word(bus, self._addr, 0x47) / 131.0
                    ok += 1
                except Exception:
                    pass  # 偶发 I2C 错误跳过
                time.sleep(0.005)
            if ok < CALIB_SAMPLES // 2:
                print(f"[MPU6050] 校准失败：采样过少 {ok}/{CALIB_SAMPLES}")
                return  # finally 自动关 bus + 重置 _running
            gbx /= ok; gby /= ok; gbz /= ok
            print(f"[MPU6050] 校准完成 bias=({gbx:.3f}, {gby:.3f}, {gbz:.3f}) °/s")

            # ── Mahony 初始化 ────────────────────────
            q0, q1, q2, q3 = 1.0, 0.0, 0.0, 0.0
            int_fbx, int_fby, int_fbz = 0.0, 0.0, 0.0
            last_time = time.monotonic()
            first_frame = True

            # ── 主循环 ───────────────────────────────
            while self._running:
                # --- 读传感器 ---
                try:
                    ax = _read_word(bus, self._addr, 0x3B) / 16384.0
                    ay = _read_word(bus, self._addr, 0x3D) / 16384.0
                    az = _read_word(bus, self._addr, 0x3F) / 16384.0
                    gx = _read_word(bus, self._addr, 0x43) / 131.0 - gbx
                    gy = _read_word(bus, self._addr, 0x45) / 131.0 - gby
                    gz = _read_word(bus, self._addr, 0x47) / 131.0 - gbz
                    temp = _read_word(bus, self._addr, 0x41) / 340.0 + 36.53
                except Exception as e:
                    # I2C 瞬时错误跳过，等待下次采样
                    time.sleep(0.001)
                    continue

                # --- dt ---
                now = time.monotonic()
                dt = now - last_time
                last_time = now
                if dt <= 0 or dt > 0.1:  # 首帧或卡顿，用默认 dt
                    dt = 0.01

                # --- 归一化加速度 ---
                ax_n, ay_n, az_n = _normalize(ax, ay, az)

                # --- Mahony 加速度修正 ---
                vx = 2.0 * (q1 * q3 - q0 * q2)
                vy = 2.0 * (q0 * q1 + q2 * q3)
                vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3

                ex = ay_n * vz - az_n * vy
                ey = az_n * vx - ax_n * vz
                ez = ax_n * vy - ay_n * vx

                int_fbx += self._ki * ex * dt
                int_fby += self._ki * ey * dt
                int_fbz += self._ki * ez * dt

                gxc = gx * math.pi / 180.0 + self._kp * ex + int_fbx
                gyc = gy * math.pi / 180.0 + self._kp * ey + int_fby
                gzc = gz * math.pi / 180.0 + self._kp * ez + int_fbz

                # --- 四元数更新（一阶龙格库塔，全部用旧值） ---
                half_dt = 0.5 * dt
                dq0 = (-q1 * gxc - q2 * gyc - q3 * gzc) * half_dt
                dq1 = ( q0 * gxc + q2 * gzc - q3 * gyc) * half_dt
                dq2 = ( q0 * gyc - q1 * gzc + q3 * gxc) * half_dt
                dq3 = ( q0 * gzc + q1 * gyc - q2 * gxc) * half_dt
                q0 += dq0; q1 += dq1; q2 += dq2; q3 += dq3
                q0, q1, q2, q3 = _normalize(q0, q1, q2, q3)

                # --- 四元数 → 欧拉角 ---
                pitch_val = 2.0 * (q0 * q2 - q1 * q3)
                pitch_val = _clamp(pitch_val, -1.0, 1.0)
                pitch = math.asin(pitch_val) * 180.0 / math.pi
                roll = math.atan2(2.0 * (q0 * q1 + q2 * q3),
                                  q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3) * 180.0 / math.pi
                yaw = math.atan2(2.0 * (q1 * q2 + q0 * q3),
                                 q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3) * 180.0 / math.pi

                # --- 写入共享状态 ---
                with self._lock:
                    self._attitude = Attitude(pitch, roll, yaw, time.monotonic())

                if first_frame:
                    self._ready.set()
                    first_frame = False

                # --- VOFA+ 串口输出（可选） ---
                if self._vofa_writer is not None:
                    try:
                        line = (f"{pitch:.2f},{roll:.2f},{yaw:.2f},"
                                f"{ax:.3f},{ay:.3f},{az:.3f},"
                                f"{gx:.2f},{gy:.2f},{gz:.2f},{temp:.1f}\n")
                        self._vofa_writer(line.encode('utf-8'))
                    except Exception:
                        pass  # 发送失败不影响姿态解算

            # ── 清理 ─────────────────────────────────
            bus.close()
            print("[MPU6050] 已停止")
        except Exception as e:
            print(f"[MPU6050] 线程异常: {e}")
        finally:
            # 保证任何退出路径都不会让 _running 残留为 True，
            # 否则后续 start() 永远静默失效。
            if bus is not None:
                try:
                    bus.close()
                except Exception:
                    pass
            self._running = False
            self.disable_serial_vofa()  # 关 VOFA+ 串口（幂等）


# ── 模块级单例 + 便捷函数 ─────────────────────────────────────

imu = MPU6050Imu()


def get_pitch():
    """获取最新 pitch (°)；IMU 未就绪时返回 None。"""
    return imu.get_pitch()


def get_roll():
    """获取最新 roll (°)；IMU 未就绪时返回 None。"""
    return imu.get_roll()


def get_yaw():
    """获取最新 yaw (°)；IMU 未就绪时返回 None。

    注意：6 轴 IMU 没有磁力计，yaw 会随时间漂移，不能作为绝对航向使用。
    """
    return imu.get_yaw()


def get_attitude():
    """获取 Attitude(pitch, roll, yaw, ts)；IMU 未就绪时返回 None。"""
    return imu.get_attitude()
