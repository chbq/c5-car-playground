# C5 Hardware Wiki

This directory is the compact, evidence-backed wiki for the C5 firmware project.
It describes the system before any CubeMX or Keil project is created.

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

## Current baseline

- System application MCU: STM32F103C8T6.
- Four wheel motors are independent bus-motor modules, not four direct MCU PWM outputs.
- Motor bus: USART3 on PB10/PB11 through the baseboard single-wire `DAT` circuit.
- Wired PC and serial-boot path: CH340 through USART1 on PA9/PA10 at 115200 baud.
- Optional independent host link: reserve USART2 on PA2/PA3, accessible from H1.
- Debug: reserve SWD on PA13/PA14; PS2 use is deferred.
- Project clock input: use the vendor-source 8 MHz HSE assumption and configure 72 MHz with PLL x9; revisit only if hardware behavior disagrees.
- The CubeMX/Keil baseline and first unverified motion implementation build successfully; no firmware has been flashed and no motor has been driven.

## Evidence labels

| Label | Meaning |
|---|---|
| Confirmed | Explicit vendor schematic/manual evidence, or mutually consistent vendor sources |
| User-observed | Physical observation explicitly supplied by the user |
| Source-derived | Vendor code behavior; useful but not sufficient to override conflicting hardware evidence |
| Unresolved | Missing, conflicting or not yet physically verified |

Unknown hardware facts remain in [unresolved.md](unresolved.md); they are never filled from generic STM32 assumptions.
