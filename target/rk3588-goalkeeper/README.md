# RK3588 守门员上位机

香橙派 RK3588 端的视觉与 C5 运动链路。本阶段只建立安全通信，不实现自动守门：

- `main.py` 保留球/球门推理，只查询并显示 STM32 链路状态；不会自动 ARM 或动车；
- `motion_link.py` 提供 `arm()`、`set_twist()`、`stop()`、`query()`；
- `motion_cli.py` 用于人工 QUERY/STOP 和架空低速限时动作；
- `doctor.py` 只读检查系统、Python、RKNN、模型、串口节点和权限；
- `state_manager.py` 仅管理 IDLE/INFERENCE，不再兼任串口协议。

模型、视频、wheel、IDE/cache 和旧 Agent 元数据不纳入 Git。

实物已通过 SSH 确认为 Orange Pi 5 Pro（RK3588S）、Orange Pi Ubuntu
22.04.5。远端 2026-07-26 视觉基线使用
`model_26.7.25_i8.rknn`、6 个推理 worker 和 `NMS_THRESH=0.2`；上述参数已合入，
模型文件仅保存在板端和忽略的本机备份中。

## 接线

HOST 目标仍为 `UART7_M2`、`/dev/ttyS7`、115200、8N1。实物 5 Pro 当前镜像
提供 `rk3588-uart7-m2.dtbo`，但尚未启用，`/dev/ttyS7` 尚不存在。

| Orange Pi 40-pin | C5 H1 | 信号 |
|---|---|---|
| 待按 5 Pro 手册确认，UART7_TX_M2 | 24，PA3/USART2_RX | Orange Pi → STM32 |
| 待按 5 Pro 手册确认，UART7_RX_M2 | 26，PA2/USART2_TX | STM32 → Orange Pi |
| 待按 5 Pro 手册确认，GND | H1-15 或 H1-16 | 共地 |

确认 5 Pro 针脚前不得接线。两板 VCC 不相连；`/dev/ttyS0` 是调试控制台，
不用于运动链路。

## 本机测试

在仓库根目录运行：

```powershell
.\tools\test-rk-host.ps1
```

测试不需要 RKNN、pyserial 或香橙派，覆盖协议黄金帧、边界、解析、ACK 和超时策略。

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

动作命令只能在轮组架空并再次获得明确授权后使用；CLI 将单轴限制在 ±200、时长限制在 2 秒，并始终尝试 STOP：

```bash
python3 motion_cli.py move --vx 100 --duration 0.5 --execute
```

`main.py` 与 CLI 使用 `/tmp` 独占锁，不能同时打开运动串口。固定帧定义见[通信协议](通信协议.md)，服务部署见[开机自启动](开机自启动使用说明.md)。

## 后续边界

下一任务才接入检测框、置信度、时间戳和 IMU 姿态，完成相机投影、场地/球定位、拦截与守门区保持。此前还需相机内外参、场地和球门尺寸、己方/对方球门区分；MPU6050 漂移 yaw 不能单独作为绝对航向。
