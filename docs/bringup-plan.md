# C5 Bring-up Plan

## Phase 0A - Hardware wiki baseline

Status: documented, with unresolved items explicitly retained.

- system requirements and boundaries;
- power and signal architecture;
- H1 and MCU pin map;
- peripheral allocation for motor, host and debug links;
- vendor evidence inventory;
- hardware and tooling blockers.

No generation, build, flash or motor output is allowed in this phase.

## Phase 0B - Optional physical checks

These checks are useful when wiring the board, but they do not block creation of the first `.ioc`:

- use 8 MHz HSE and PLL x9 from the vendor source unless hardware behavior disagrees;
- verify physical core/base revision silk when convenient;
- identify H1 pin 1 and continuity-check planned USART2/SWD pins;
- locate an NRST access point if available;
- document 3.3 V, 5 V and VS rails without driving motors;
- keep motor modules disconnected when a check does not require them.

## Phase 0C - Reproducible toolchain

Status: complete on the current machine.

- initialize Git before generated files exist;
- create ignored `tools/local.env.ps1` from the template;
- make `doctor.ps1` detect the actual D-drive installations;
- select and record CubeMX, CubeF1, Keil DFP and ARM compiler versions;
- run doctor and save its exit code/reports;
- decide the exact SWD and serial-boot cable mappings.

## Phase 1 - Minimal no-motor project

Status: complete and built with AC5.06u7.

After the toolchain inputs are pinned:

- confirmed system clock;
- SWD retained;
- USART1 CH340 diagnostic/boot path;
- USART3 initialized without sending motion commands;
- USART2 pins reserved, not necessarily enabled;
- explicit safe startup state and fault reporting;
- CubeMX regeneration and Keil command-line build;
- zero build errors, warnings recorded;
- no automatic flash.

## Phase 2 - Flash and boot

- connect through the chosen debug/programming path;
- flash only after a successful build and explicit user confirmation;
- verify image, reset and diagnostic boot message;
- confirm reset/startup never produces motor motion.

## Phase 3 - Bus and single-wheel acceptance

The chassis must be raised. Read or verify device IDs first, then test one physical wheel at a time with low speed, bounded duration and automatic stop. Communication-loss behavior must be tested before any vehicle-level motion.

## Phase 4 - Mecanum vehicle commands

The unitless `vx`, `vy` and `wz` mixer and bounded safety state machine are
implemented ahead of hardware access so they can be reviewed and host-tested.
They remain disabled from autonomous use. Enable vehicle-level commands only
after all four physical wheel mappings, motor directions and timeout behavior
pass Phase 3.

## Phase 5 - Optional expansion

Add the independent USART2 host link, sensors or other peripherals as separately scoped tasks. Use C25 behavior or algorithms only after the C5 baseline is stable.
