# C5 Pin and Peripheral Budget

## Goal-driven reservation

| Priority | Function | MCU resource | Board path | Policy |
|---|---|---|---|---|
| Fixed | Wired PC, log and serial boot | USART1 PA9/PA10 | CH340 and USB connector | Keep |
| Fixed | Four-wheel motor bus | USART3 PB10/PB11 | H1 to baseboard DAT circuit | Keep |
| Fixed | Debug/programming | PA13 SWDIO, PA14 SWCLK | H1 pins 11/12 | Keep; do not initialize PS2 |
| Reserved | Independent host expansion | USART2 PA2/PA3 | H1 pins 26/24 | Reserve for Bluetooth, TTL UART or RS485 |
| Reserved if RS485 | Driver direction | PA11 candidate | H1 pin 14 / KEY2 net | Reserve until transceiver choice |
| Board-owned | External Flash | SPI2 PB12-PB15 | W25Q64; PB13 also LED | Preserve initially |

## H1 connector

The schematic numbers H1 as two 16-pin rows. Confirm physical pin-1 orientation from silk or continuity before making a cable.

| H1 | Net | MCU | H1 | Net | MCU |
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

PA8 is physically shared by KEY1 and IR. Sensor connectors S1 and S2 cross-connect the same PA0/PA1 pair and are not four independent signals.

## Other MCU connections

| MCU pin(s) | Connection | Constraint |
|---|---|---|
| PA9/PA10 | CH340 USART1 | Not on H1; fixed diagnostic/download path |
| PB2/BOOT1 | Grounded in core schematic | Not available as a free GPIO |
| PB12/PB13/PB14/PB15 | W25Q64 NSS/SCK/MISO/MOSI | SPI2; PB13 also drives active-low LED |
| PD0/PD1 | 8 MHz HSE crystal | Value comes from vendor source and is accepted as the project input |
| PC13/PC14/PC15 | Marked not connected | Not available without hardware modification |
| BOOT0/NRST | Automatic serial-download and reset circuits | Not exposed on H1 |

## Sensor connectors

Each connector carries two direct MCU signals, GND and selectable `VCC_Sensor` (3.3 V or 5 V).

| Connector | Signals | Vendor example |
|---|---|---|
| S1 | PA0, PA1 | Dual line-tracking sensor, digital high/low |
| S2 | PA1, PA0 | Duplicate/crossed access to S1 signals |
| S3 | PA2, PB0 | Ultrasonic module |
| S4 | PA3, PB1 | No baseline assignment |
| S5 | PA4, PA6 | No baseline assignment |
| S6 | PA5, PA7 | No baseline assignment |

All ten unique signal pins are ADC-capable on STM32F103C8T6, but the vendor examples also use them as digital GPIO. `SSA` and `SSD` are schematic net names; vendor documentation does not prove that one is always analog and the other always digital.

The baseboard contains no visible signal-level conversion on these lines. A sensor powered from 5 V must still present MCU-safe signal levels.

## Peripheral alternatives and conflicts

| Peripheral | Candidate pins | Board-level conflict |
|---|---|---|
| USART2 | PA2/PA3 | Sensor3 `SSA3` and Sensor4 `SSA4` |
| SPI1 | PA4-PA7 | Sensor5/6 signals |
| I2C1 | PB6/PB7 or remap PB8/PB9 | PWM-servo outputs DJ3/DJ4 or DJ1/DJ2 |
| I2C2 | PB10/PB11 | Motor bus; unavailable |
| TIM1 channels | PA8-PA11 | IR/KEY1, CH340 and KEY2 |
| TIM2 channels | PA0-PA3 | Sensors and reserved USART2 |
| TIM3 channels | PA6/PA7/PB0/PB1 | Sensor signals |
| TIM4 channels | PB6-PB9 | Four PWM-servo outputs; valuable deferred resource |
| CAN | PA11/PA12 or remap PB8/PB9 | KEY2/PS2 or servo outputs; no onboard transceiver |
| Native USB | PA11/PA12 | No connection to the board USB socket, which terminates at CH340 |

Official MCU alternate-function reference: [STM32F103x8/B datasheet](https://www.st.com/resource/en/datasheet/CD00161566.pdf).
