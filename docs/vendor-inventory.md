# C5 Vendor Inventory

## Scope

Immutable evidence root: `reference/c5-vendor/`.

The C5 package currently contains 58 files:

| Type | Count |
|---|---:|
| PDF | 20 |
| TXT | 15 |
| ZIP | 4 |
| EXE | 4 |
| PNG | 3 |
| HEX | 3 |
| MP4 | 3 |
| PPTX | 2 |
| INI | 2 |
| INO | 1 |
| MD placeholder | 1 |

Package sections contain 56 files plus two files at the evidence root:

| Section | Files | Relevance |
|---|---:|---|
| `000-快速上手` | 1 | Product overview |
| `001-文档教程` | 18 | Primary manuals, ID map and module descriptions |
| `002-视频教程` | 9 | Supplemental demonstrations; not yet audited frame by frame |
| `003-源码例程` | 14 | Factory image, source archive and auxiliary-controller examples |
| `004-软件工具` | 13 | Schematics, CH340, FlyMcu, Keil material and vendor host software |
| `005-拓展资料` | 1 | External link list |

## Primary hardware evidence

| Evidence | Use |
|---|---|
| `核心板-ZL-KPZ32_V3.pdf` | MCU, CH340, HSE, W25Q64, LED, boot/reset and H1 mapping |
| `底板-ZL-KPZ V3.4.pdf` | Power rails, DAT conversion and all baseboard connectors |
| `1.7、主控板学习-STM32-V1.0.pdf` | MCU identity, supply range, board interfaces and serial download workflow |
| `1.4.2、C5小车设备ID分布图-V1.0.pdf` | C5 wheel positions and IDs 006-009 |
| `2、总线电机介绍-V1.0.pdf` | Bus-motor supply, protocol, command ranges and broadcast ID |
| `1.9、小车功能代码学习-STM32-V1.0.pdf` | Vendor uses of S1 line tracking, S3 ultrasonic and serial command flow |
| `Carbot(C5)-STM32智能车出厂程序-250518.zip` | Source-level pin, UART, clock and startup evidence |

## Source-project findings

- No vendor `.ioc` exists in the C5 package.
- The project uses the legacy STM32 Standard Peripheral Library and bare metal.
- The source explicitly configures USART1 PA9/PA10, USART2 PA2/PA3 and USART3 PB10/PB11 at 115200.
- The source expects an 8 MHz HSE and configures PLL x9 for 72 MHz.
- The Keil target/device is C8, but the active density macro/startup selection is internally inconsistent and cannot be copied.

The vendor source remains evidence only; it is not the long-lived target project.
