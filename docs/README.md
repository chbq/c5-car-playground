# C5 Hardware Wiki

This directory is the compact, evidence-backed wiki for the C5 firmware project.
It covers the hardware baseline, generated firmware and current control design.

## Pages

| Page | Purpose |
|---|---|
| [hardware.md](hardware.md) | Requirements, system boundary, power and signal architecture |
| [pinmap.md](pinmap.md) | H1 connector, MCU pin ownership and peripheral budget |
| [unresolved.md](unresolved.md) | Conflicts, missing evidence and required physical checks |
| [bringup-plan.md](bringup-plan.md) | Evidence, tooling and no-motor bring-up gates |
| [vendor-inventory.md](vendor-inventory.md) | C5 vendor evidence inventory and primary sources |
| [acceptance.md](acceptance.md) | Acceptance gates for environment, build, flash and motors |
| [official-tooling-notes.md](official-tooling-notes.md) | Local toolchain assumptions and pending verification |
| [motion-control.md](motion-control.md) | Vendor motion evidence, HAL/App design, safety behavior and pending calibration |
| [ps2-control.md](ps2-control.md) | PS2 protocol, SWD sharing, KEY1 mode switch and remote-control safety design |

## Current baseline

- System application MCU: STM32F103C8T6.
- Four wheel motors are independent bus-motor modules, not four direct MCU PWM outputs.
- Motor bus: USART3 on PB10/PB11 through the baseboard single-wire `DAT` circuit.
- Wired PC and serial-boot path: CH340 through USART1 on PA9/PA10 at 115200 baud.
- Optional independent host link: reserve USART2 on PA2/PA3, accessible from H1.
- Debug/control: boot with SWD on PA13/PA14; a deliberate KEY1 long press may
  release SWD and assign PA12-PA15 to PS2 until another long press or reset.
- Project clock input: use the vendor-source 8 MHz HSE assumption and configure 72 MHz with PLL x9; revisit only if hardware behavior disagrees.
- The CubeMX/Keil baseline and first unverified motion implementation build
  successfully. The PS2/SWD dual-mode implementation also passes host tests,
  CubeMX regeneration and AC5 compilation. No firmware has been flashed and no
  motor has been driven.

## Evidence labels

| Label | Meaning |
|---|---|
| Confirmed | Explicit vendor schematic/manual evidence, or mutually consistent vendor sources |
| User-observed | Physical observation explicitly supplied by the user |
| Source-derived | Vendor code behavior; useful but not sufficient to override conflicting hardware evidence |
| Unresolved | Missing, conflicting or not yet physically verified |

Unknown hardware facts remain in [unresolved.md](unresolved.md); they are never filled from generic STM32 assumptions.
