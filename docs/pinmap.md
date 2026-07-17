# C5 引脚与外设预算

## 资源分配

| 优先级 | 功能 | MCU 资源 | 板级路径 | 策略 |
|---|---|---|---|---|
| 固定 | USB 上位机、日志、串口下载 | USART1 PA9/PA10 | CH340、USB | 保留 |
| 固定 | 四轮电机总线 | USART3 PB10/PB11 | H1 → DAT 电路 | 保留 |
| 条件复用 | 调试/烧录 | PA13 SWDIO、PA14 SWCLK | H1 11/12 | 上电保留；KEY1 长按后才交给 PS2 |
| 预留 | 独立上位机 | USART2 PA2/PA3 | H1 26/24 | 蓝牙、TTL UART 或 RS485 |
| RS485 可选 | 收发方向 | 候选 PA11 | H1 14 / KEY2 | 选定收发器前保留 |
| 板载占用 | 外部 Flash | SPI2 PB12–PB15 | W25Q64；PB13 兼作 LED | 暂保留 |

## H1 接口

H1 为两排各 16 针。制作线缆前用丝印或通断确认 1 脚方向。

| H1 | 网络 | MCU | H1 | 网络 | MCU |
|---:|---|---|---:|---|---|
| 1 | KEY1 | PA8 | 32 | TXD3 | PB10 |
| 2 | IR | PA8 | 31 | RXD3 | PB11 |
| 3 | DJ0 | PB3 | 30 | SSA1 | PA0 |
| 4 | DJ1 | PB8 | 29 | SSD1 | PA1 |
| 5 | DJ2 | PB9 | 28 | SSA2 | PA1 |
| 6 | DJ3 | PB6 | 27 | SSD2 | PA0 |
| 7 | DJ4 | PB7 | 26 | SSA3 | PA2 |
| 8 | DJ5 | PB4 | 25 | SSD3 | PB0 |
| 9 | BEEP | PB5 | 24 | SSA4 | PA3 |
| 10 | PS7 | PA12 | 23 | SSD4 | PB1 |
| 11 | PS6 | PA13 | 22 | SSA5 | PA4 |
| 12 | PS2 | PA14 | 21 | SSD5 | PA6 |
| 13 | PS1 | PA15 | 20 | SSA6 | PA5 |
| 14 | KEY2 | PA11 | 19 | SSD6 | PA7 |
| 15 | GND | - | 18 | VCC-3.3 | - |
| 16 | GND | - | 17 | VCC-5.0 | - |

PA8 同时标为 KEY1 和 IR。S1/S2 交叉复用同一对 PA0/PA1，并非四路独立信号。

## 其他板载连接

| MCU 引脚 | 连接 | 约束 |
|---|---|---|
| PA9/PA10 | CH340 USART1 | 不在 H1；固定诊断/下载链路 |
| PB2/BOOT1 | 原理图接地 | 不作普通 GPIO |
| PB12–PB15 | W25Q64 SPI2 | PB13 兼作低电平亮 LED |
| PD0/PD1 | 8 MHz HSE | 已接受为工程输入 |
| PC13–PC15 | 标为未连接 | 不改板时不可用 |
| BOOT0/NRST | 自动下载/复位电路 | 未引到 H1 |

## 传感器接口

每口含两路 MCU 信号、GND 和可选 3.3/5 V `VCC_Sensor`。

| 接口 | 信号 | 商家示例 |
|---|---|---|
| S1 | PA0、PA1 | 双路数字巡线 |
| S2 | PA1、PA0 | 与 S1 重复/交叉 |
| S3 | PA2、PB0 | 超声波 |
| S4 | PA3、PB1 | 未固定 |
| S5 | PA4、PA6 | 未固定 |
| S6 | PA5、PA7 | 未固定 |

10 个唯一信号脚都支持 ADC，也可作数字 GPIO。`SSA`/`SSD` 只是网络名，不能据此断言模拟/数字用途。底板未见电平转换，5 V 供电传感器仍须保证输出对 MCU 安全。

## 外设冲突

| 外设 | 候选引脚 | 冲突 |
|---|---|---|
| USART2 | PA2/PA3 | S3 `SSA3`、S4 `SSA4` |
| SPI1 | PA4–PA7 | S5/S6 |
| I2C1 | PB6/PB7 或 PB8/PB9 重映射 | DJ3/DJ4 或 DJ1/DJ2 |
| I2C2 | PB10/PB11 | 电机总线，不可用 |
| TIM1 | PA8–PA11 | IR/KEY1、CH340、KEY2 |
| TIM2 | PA0–PA3 | 传感器、USART2 |
| TIM3 | PA6/PA7/PB0/PB1 | 传感器 |
| TIM4 | PB6–PB9 | 四路舵机口，暂保留 |
| CAN | PA11/PA12 或 PB8/PB9 重映射 | KEY2/PS2 或舵机口；板上无收发器 |
| 原生 USB | PA11/PA12 | 板载 USB 实际接 CH340 |

MCU 复用功能参考：[STM32F103x8/B 数据手册](https://www.st.com/resource/en/datasheet/CD00161566.pdf)。
