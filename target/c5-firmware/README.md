# C5 Target Firmware

This is the long-lived STM32CubeMX + Keil target project for the C5 car.

The baseline is generated from `c5-firmware.ioc` for STM32F103C8T6 with:

- 8 MHz HSE and 72 MHz system clock;
- SWD on PA13/PA14;
- USART1 diagnostic/CH340 link on PA9/PA10;
- USART2 host expansion link on PA2/PA3;
- USART3 motor bus on PB10/PB11;
- active-low PB13 status LED, initially high/off.

It contains CubeMX initialization only. It sends no UART or motor command.

Suggested application layout after CubeMX generation:

```text
App/
  Inc/
  Src/
Core/
Drivers/
MDK-ARM/
```

Regenerate and rebuild from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\generate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 -Rebuild
```
