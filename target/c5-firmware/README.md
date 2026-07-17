# C5 Target Firmware

This is the long-lived STM32CubeMX + Keil target project for the C5 car.

The baseline is generated from `c5-firmware.ioc` for STM32F103C8T6 with:

- 8 MHz HSE and 72 MHz system clock;
- SWD on PA13/PA14;
- USART1 diagnostic/CH340 link on PA9/PA10;
- USART2 host expansion link on PA2/PA3;
- USART3 motor bus on PB10/PB11;
- active-low PB13 status LED, initially high/off.

The `App/` layer now contains the first unverified motion implementation. At
startup it sends the vendor broadcast stop frame on USART3 and then services
the motion timeout/fault state machine. It does not schedule any movement or
parse host commands.

Application layout:

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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\test-host.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 -Rebuild
```

`generate.ps1` calls `sync-keil-project.ps1` so the generated MDK project always
contains `App/Src/*.c` and `App/Inc`. None of these commands flash hardware.
