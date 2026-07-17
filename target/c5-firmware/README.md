# C5 Target Firmware

This is the long-lived STM32CubeMX + Keil target project for the C5 car.

The baseline is generated from `c5-firmware.ioc` for STM32F103C8T6 with:

- 8 MHz HSE and 72 MHz system clock;
- SWD on PA13/PA14 at boot, dynamically shareable with PS2 control;
- USART1 diagnostic/CH340 link on PA9/PA10;
- USART2 host expansion link on PA2/PA3;
- USART3 motor bus on PB10/PB11;
- active-low PB13 status LED, initially high/off.
- KEY1 on PA8 as an input pull-up (active-low assumption pending hardware check).

The `App/` layer now contains the first unverified motion implementation. At
startup it sends the vendor broadcast stop frame on USART3 and then services
the motion timeout/fault state machine. It does not schedule any movement or
parse host commands.

The firmware includes one-image runtime switching between debug and PS2 modes.
PS2 mode uses PA12 CLK, PA13 ATT, PA14 CMD and PA15 DAT. Entering it requires a
KEY1 long press and an unplugged debug probe; reset always restores debug mode.

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
