# 香橙派 HOST 运动链路

## 范围

Phase 4 打通“香橙派发送 `vx/vy/wz`，STM32 安全执行并回报状态”。`main.py`
默认 IDLE/INFERENCE 不自动 ARM；Phase 5A 仅在显式
`--mode ball-yaw-test --execute` 下限时发送球心转向。自动守门另立任务。

## 物理链路

实物经 SSH 确认为 Orange Pi 5 Pro（RK3588S）。默认链路为：

```text
Orange Pi USB-A host → USB 数据线 → 核心板 CH340 → USART1 PA10/PA9 → STM32
```

参数为 115200、8N1。无需启用 GPIO overlay、连接 40-pin 或另接共地线；USB 线已含
数据、地和 VBUS。VBUS 可给核心板逻辑供电，但不能给总线电机供电。PC 串口下载和
Orange Pi HOST 共用 CH340，同一时刻只由一台 USB 主机连接并打开。

Linux 默认按以下顺序解析端口：`C5_HOST_PORT`、`/dev/c5-host`、唯一 CH340
`/dev/serial/by-id/...`、唯一 `/dev/ttyUSB*`。多个 USB 串口时必须显式指定。
CH340 DTR/RTS 接入核心板自动下载电路；Python 在 `open()` 前撤销两信号，但驱动层
瞬态仍须实测。USART2 PA2/PA3 保留为 3.3 V 扩展链路，不参与本阶段默认 HOST。
SSH 密钥登录是主要远程通道；NoMachine 只用于观察 OpenCV 窗口。

## 控制权与安全

- 复位进入 HOST 模式，保留 SWD、主动停车、HOST 未解锁；
- 合法 ARM 先停车再解锁；非零 TWIST 只在 HOST+ARMED 时执行；
- TWIST 20 Hz 刷新，动作保持 150 ms；200 ms 无合法 HOST 命令则停车并解除 ARM；
- 零 TWIST 停车但保持 ARM；
- KEY1 长按先停车并解除 HOST，再释放 SWD 进入 PS2；退出 PS2 后需重新 ARM；
- PS2 模式拒绝 ARM/TWIST，QUERY 可用，STOP 在任何模式停车并解除当前控制状态；
- 坏帧、UART 错误、接收队列溢出和运动故障均停车；
- PB13 保持原 PS2 指示语义，不用于 HOST 状态。

STM32 使用 USART1 逐字节中断接收和 4 项事件队列；ISR 只解析/排队，不发送电机指令。主循环完成控制仲裁、USART1 状态回复和 USART3 电机发送。

## 协议摘要

命令和状态均为固定 11 字节，CRC-8/ATM 覆盖 Byte2–Byte9：

```text
A5 5A TYPE SEQ VX_L VX_H VY_L VY_H WZ_L WZ_H CRC8
A5 5A 80 ACK_SEQ RESULT MODE HOST_STATE MOTION_STATE ERR_L ERR_H CRC8
```

ARM=`01`、TWIST=`02`、STOP=`03`、QUERY=`04`。三轴为小端 `int16_t`，有效范围 `[-1000,1000]`；非 TWIST 的三轴必须为零。完整字段与黄金帧见 [`target/rk3588-goalkeeper/通信协议.md`](../target/rk3588-goalkeeper/通信协议.md)。

## 软件结构

| 位置 | 职责 |
|---|---|
| `c5_host_protocol` | 固定帧解析、校验、状态编码 |
| `c5_host_control` | ARM、TWIST、STOP、200 ms 看门狗 |
| `c5_host_uart_hal` | 所选 HOST UART 中断收包、小事件队列、状态发送 |
| `C5_Control` | HOST/PS2 控制权与全局停车仲裁 |
| `motion_protocol.py` | Python 同构协议实现 |
| `serial_transport.py` | CH340 自动发现、DTR/RTS 预置和串口打开 |
| `motion_link.py` | ACK、状态超时、ARM 门控、端口锁 |
| `motion_cli.py` | 默认 QUERY；显式低速、限时测试 |

## 验收顺序

1. Windows 主机 C/Python 测试、CubeMX 生成、AC5 和完整 verify；
2. SSH 只读环境检查，确认板型、系统、Python/RKNN；
3. USB 连接核心板，确认 `lsusb`、`/dev/serial/by-id/...` 和读写权限；
4. 重复打开/关闭端口，确认 DTR/RTS 不会使 MCU 卡在 Bootloader；
5. 烧录本阶段固件后只做 QUERY/ARM/STOP；
6. 架空轮组并再次获得明确授权后，分别低速测 `vx`、`vy`、`wz`、STOP、发送中断后的超时停车和 HOST/PS2 互斥；
7. 本阶段不做落地自动行驶。

SSH、CH340 枚举与稳定路径、USART1 双向通信均已实测。QUERY/STOP、零速
ARM/TWIST、200 ms 自动解除 ARM、20 次重复开关和坏 CRC 恢复通过，错误响应后链路
保持可用。系统自带 `brltty-udev` 曾抢占 CH340；现已将该 unit mask，重启后保持
`masked/inactive`，CH340 自动恢复为 `ttyUSB0`，doctor 和 QUERY 均通过。架空
`vx/vy/wz=100`、`vx=50,vy=±50` 两组斜移和 STOP 均实测通过；
发送进程运行 1.2 秒后被 `SIGKILL`，轮组可见自动停车，随后 QUERY 为
`DISARMED/STOPPED/errors=0`。USB 物理拔线和 HOST/PS2 互斥尚未验收。
