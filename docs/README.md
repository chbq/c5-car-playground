# C5 项目 Wiki

本目录集中记录硬件证据、固件设计、验收状态和未决问题。

## 文档

| 页面 | 内容 |
|---|---|
| [hardware.md](hardware.md) | 系统边界、电源与信号结构 |
| [pinmap.md](pinmap.md) | H1、MCU 引脚归属和外设预算 |
| [unresolved.md](unresolved.md) | 冲突、缺失证据和实物检查项 |
| [bringup-plan.md](bringup-plan.md) | 分阶段调通计划 |
| [vendor-inventory.md](vendor-inventory.md) | 商家资料清单与主要证据 |
| [acceptance.md](acceptance.md) | 环境、构建、烧录、电机和 PS2 验收门槛 |
| [official-tooling-notes.md](official-tooling-notes.md) | 本机工具链基线 |
| [motion-control.md](motion-control.md) | 电机协议、麦轮运动和安全策略 |
| [ps2-control.md](ps2-control.md) | PS2、SWD 复用和遥控策略 |
| [host-link.md](host-link.md) | 香橙派 USB/CH340 协议、控制权和验收顺序 |

## 当前基线

- MCU：STM32F103C8T6。
- 四轮为独立总线电机，不是 MCU 四路直驱 PWM。
- 电机总线：USART3 PB10/PB11，经底板单线 `DAT` 电路。
- 默认 HOST/串口下载：Orange Pi 或 PC USB → CH340 → USART1 PA9/PA10，115200。
- 扩展串口：USART2 PA2/PA3 经 H1 引出，保留给后续 3.3 V UART/外置 RS485。
- 调试/遥控：上电使用 PA13/PA14 SWD；KEY1 长按后 PA12–PA15 切换为 PS2。
- 时钟：8 MHz HSE，PLL ×9 至 72 MHz。
- 当前镜像已烧录；PS2 模拟模式、KEY1 切换、架空和整车麦轮三轴运动已实测。
- 手柄关机后接收器仍返回合法帧，无线失联停车尚未闭环。
- HOST 固定帧、显式 ARM、200 ms 看门狗和 PS2 互斥已完成软件验证，实物串口验收待做。

## 证据等级

| 等级 | 含义 |
|---|---|
| 已确认 | 原理图/手册明确，或多份商家资料一致 |
| 用户观察 | 用户明确提供的实物观察 |
| 源码推断 | 来自商家代码，不能覆盖冲突的硬件证据 |
| 未决 | 证据缺失、冲突或尚未实测 |

未决事实统一记录在 [unresolved.md](unresolved.md)。
