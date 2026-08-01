# RK3588 守门员上位机

香橙派 RK3588 端的视觉与 C5 运动链路。当前增加球心转向和麦轮横移测试：

- `main.py` 默认只推理/显示；显式 `ball-yaw-test --execute` 才允许限时 `wz`；
- `ball_yaw_control.py` 提供像素控制器、20 Hz 会话和丢球停车；
- `ball_strafe_control.py` 只生成 `vy`，固定 `vx/wz=0`；
- `ball_follow_control.py` 按球左右生成 `vx/wz`、按框远近生成 `vy`；
- `ball-fov-test` 在 5C 基础上增加边缘转向优先、预测和滞回；
- `control_log.py` 以 20 Hz 记录检测、三轴、控制状态和 IMU；
- `motion_link.py` 提供 `arm()`、`set_twist()`、`stop()`、`query()`；
- `motion_cli.py` 用于人工 QUERY/STOP 和架空低速限时动作；
- `doctor.py` 只读检查系统、Python、RKNN、模型、串口节点和权限；
- `state_manager.py` 仅管理 IDLE/INFERENCE，不再兼任串口协议。

模型、视频、wheel、IDE/cache 和旧 Agent 元数据不纳入 Git。

实物已通过 SSH 确认为 Orange Pi 5 Pro（RK3588S）、Orange Pi Ubuntu
22.04.5。远端 2026-07-26 视觉基线使用
`model_26.7.25_i8.rknn`、6 个推理 worker 和 `NMS_THRESH=0.2`；上述参数已合入，
模型文件仅保存在板端和忽略的本机备份中。`brltty-udev.service` 已 mask，
重启后 CH340 稳定枚举；不需要删除 brltty 软件包。

## 接线

HOST 使用 115200、8N1 的 USB 串口链路：

```text
Orange Pi USB-A → USB 数据线 → 核心板 CH340 → STM32 USART1 PA9/PA10
```

不接 40-pin 或 H1。端口默认设为 `auto`：优先 `C5_HOST_PORT`、`/dev/c5-host`
和唯一 CH340 `/dev/serial/by-id/...`，最后才接受唯一 `/dev/ttyUSB*`。多个串口时
用环境变量或 `--port` 指定。打开前会撤销 DTR/RTS，仍须实测核心板自动下载电路是否
出现复位瞬态。USART2 PA2/PA3 保留扩展，不再依赖 UART7 overlay。

## 本机测试

在仓库根目录运行：

```powershell
.\tools\test-rk-host.ps1
```

测试不需要 RKNN、OpenCV、pyserial 或香橙派，覆盖协议、ACK、超时和球心控制。

## 板端检查与使用

先用 SSH 密钥登录；NoMachine 仅在观察 OpenCV 窗口时使用。复制
`tools/local.env.example.ps1` 为忽略的 `tools/local.env.ps1`，配置板端目标后可从仓库根目录执行只读检查：

```powershell
.\tools\rk-doctor.ps1
```

板端安装运行依赖：

```bash
python3 -m pip install -r requirements-runtime.txt
python3 doctor.py
python3 motion_cli.py                 # 默认仅 QUERY
python3 motion_cli.py stop
```

连接后可先确认设备，不打开运动链路：

```bash
lsusb
ls -l /dev/serial/by-id/ /dev/ttyUSB* 2>/dev/null
```

动作命令只能在轮组架空并再次获得明确授权后使用；CLI 将单轴限制在 ±200、时长限制在 2 秒，并始终尝试 STOP：

```bash
python3 motion_cli.py move --vx 100 --duration 0.5 --execute
```

`main.py` 与 CLI 使用按解析后设备路径生成的 `/tmp` 独占锁，不能同时打开运动串口。
固定帧定义见[通信协议](通信协议.md)，服务部署见[开机自启动](开机自启动使用说明.md)。

无运动检查：

```bash
python3 main.py --headless --mode inference
python3 main.py --headless --mode ball-yaw-test --duration 10
```

第二条只打印 `x/error/wz`。架空轮组并再次明确授权后，才增加
`--max-wz 100 --execute`。控制和验收见
[`docs/ball-yaw-control.md`](../../docs/ball-yaw-control.md)。

横移模式默认也是 dry-run：

```bash
python3 main.py --headless --mode ball-strafe-test
```

默认参数为 `vy=250..800`、`Kp=1000`、死区 0.10、单周期变化 120。
实物横移必须再次明确授权后才增加 `--execute`。详见
[`docs/ball-strafe-control.md`](../../docs/ball-strafe-control.md)。

首轮实测发现当前相机/底盘需要 `lateral_sign=-1`；修正后 30 秒下地横移闭环
通过。该模式固定 `wz=0`，因此车头不主动转向。

追球动作默认 dry-run：

```bash
python3 main.py --headless --mode ball-follow-test
```

相机位于车右侧：左/右球对应正/负 `vx`，远/近球对应正/负 `vy`，`wz` 负责转向。
每次运行自动在 `logs/` 写逐周期 CSV；明确授权后才增加 `--execute`。详见
[`docs/ball-follow-control.md`](../../docs/ball-follow-control.md)。

三轴版本已完成 30 秒实车验收；左右、前后、转向、无目标零速和到时 STOP 均通过。

窄视角保护默认 dry-run：

```bash
python3 main.py --headless --mode ball-fov-test
```

默认在预测误差达到 0.55 时进入边缘区，回落至 0.30 才退出；边缘区平移缩至 25%，
`wz` 提高到 60–260。最多使用 150 ms 最近可靠观测做仅转向预测，之后归零等待。
CSV 额外记录滤波/预测误差、误差速度、区域、数据年龄和丢帧数。实车仍必须再次
明确授权后才增加 `--execute`。

独立 staging `c5-goalkeeper-staging-phase5d-fov-20260801` 已通过板端 65 项测试、
compileall、CLI 和 5 秒无球 dry-run；约 56 FPS、58 行 CSV、全程未 ARM，最终 QUERY
为 `HOST/DISARMED/STOPPED/errors=0`。

## 后续边界

Phase 5A 只消费球心、置信度和时间戳产生原地 `wz`。相机投影、场地/球定位、
拦截与守门区保持仍需内外参、场地和球门尺寸、己方/对方球门区分；
MPU6050 漂移 yaw 不能单独作为绝对航向。

实测已确认 `yaw_sign=+1`、左右转向、中央零速、丢球零速等待、恢复控制和
30 秒到时停车；15 秒与 30 秒下地测试均通过。

下地测试使用固定 `ground-check`/`ground-demo` 预设，但仍必须显式传入
`--mode ball-yaw-test --execute`；参数和顺序见球心转向文档。
