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

## 当前基线

- MCU：STM32F103C8T6。
- 四轮为独立总线电机，不是 MCU 四路直驱 PWM。
- 电机总线：USART3 PB10/PB11，经底板单线 `DAT` 电路。
- 诊断/串口下载：CH340 → USART1 PA9/PA10，115200。
- 独立上位机预留：USART2 PA2/PA3，可从 H1 引出。
- 调试/遥控：上电使用 PA13/PA14 SWD；KEY1 长按后 PA12–PA15 切换为 PS2。
- 时钟：8 MHz HSE，PLL ×9 至 72 MHz。
- CubeMX/Keil、麦轮运动和 PS2 双模式软件均已验证；尚未烧录和驱动电机。

## 证据等级

| 等级 | 含义 |
|---|---|
| 已确认 | 原理图/手册明确，或多份商家资料一致 |
| 用户观察 | 用户明确提供的实物观察 |
| 源码推断 | 来自商家代码，不能覆盖冲突的硬件证据 |
| 未决 | 证据缺失、冲突或尚未实测 |

未决事实统一记录在 [unresolved.md](unresolved.md)。
