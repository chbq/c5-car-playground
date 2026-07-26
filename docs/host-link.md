# 香橙派 HOST 运动链路

## 范围

本阶段只打通“香橙派发送 `vx/vy/wz`，STM32 安全执行并回报状态”。`main.py` 不自动 ARM、不根据检测结果动车；自动守门另立任务。

## 物理链路

实物经 SSH 确认为 Orange Pi 5 Pro（RK3588S），不是前期假定的 5 Plus。目标仍为
`UART7_M2`、`/dev/ttyS7`、115200、8N1；当前镜像包含
`rk3588-uart7-m2.dtbo`，但 overlay 尚未启用，设备节点尚不存在。

| Orange Pi 40-pin | C5 H1 | 方向 |
|---|---|---|
| 待按 5 Pro 手册确认，TX | 24，PA3/USART2_RX | Orange Pi → C5 |
| 待按 5 Pro 手册确认，RX | 26，PA2/USART2_TX | C5 → Orange Pi |
| 待按 5 Pro 手册确认，GND | 15 或 16，GND | 共地 |

前期按 5 Plus 记录的 pin 24/26 暂停使用，完成 5 Pro 手册核对前不得接线。
不连接两板 VCC。`/dev/ttyS0` 是调试控制台，不使用。SSH 密钥登录是主要
远程通道；NoMachine 只用于观察 OpenCV 窗口。

## 控制权与安全

- 复位进入 HOST 模式，保留 SWD、主动停车、HOST 未解锁；
- 合法 ARM 先停车再解锁；非零 TWIST 只在 HOST+ARMED 时执行；
- TWIST 20 Hz 刷新，动作保持 150 ms；200 ms 无合法 HOST 命令则停车并解除 ARM；
- 零 TWIST 停车但保持 ARM；
- KEY1 长按先停车并解除 HOST，再释放 SWD 进入 PS2；退出 PS2 后需重新 ARM；
- PS2 模式拒绝 ARM/TWIST，QUERY 可用，STOP 在任何模式停车并解除当前控制状态；
- 坏帧、UART 错误、接收队列溢出和运动故障均停车；
- PB13 保持原 PS2 指示语义，不用于 HOST 状态。

STM32 使用 USART2 逐字节中断接收和 4 项事件队列；ISR 只解析/排队，不发送电机指令。主循环完成控制仲裁、USART2 状态回复和 USART3 电机发送。

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
| `c5_host_uart_hal` | USART2 中断收包、小事件队列、状态发送 |
| `C5_Control` | HOST/PS2 控制权与全局停车仲裁 |
| `motion_protocol.py` | Python 同构协议实现 |
| `motion_link.py` | ACK、状态超时、ARM 门控、端口锁 |
| `motion_cli.py` | 默认 QUERY；显式低速、限时测试 |

## 验收顺序

1. Windows 主机 C/Python 测试、CubeMX 生成、AC5 和完整 verify；
2. SSH 只读环境检查，确认板型、系统、Python/RKNN；
3. 核对 5 Pro 40-pin 并启用 UART7_M2，确认 `/dev/ttyS7` 和权限；
4. UART7 本地回环；
5. 接 STM32 后只做 QUERY/ARM/STOP；
6. 再次获得明确授权后烧录；
7. 架空轮组分别低速测 `vx`、`vy`、`wz`、STOP、发送中断后的超时停车和 HOST/PS2 互斥；
8. 本阶段不做落地自动行驶。

SSH 与板型/系统只读检查已完成；UART overlay、针脚、回环、STM32 串口互通、
烧录和动作验收均未执行。
