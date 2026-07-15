# Repository Instructions

## Mission

Build and maintain a clean STM32CubeMX + Keil firmware project for the C5
four-wheel mecanum car. During the initial bring-up, do not use C25 code.

## Sources of truth

Hardware facts must come from one or more of:

1. schematics and vendor documentation in `reference/c5-vendor/`;
2. vendor `.ioc` files;
3. vendor Keil projects and startup/linker configuration;
4. mutually consistent vendor example code;
5. measurements or observations explicitly recorded by the user.

Never invent MCU variants, pins, timers, channels, interrupt priorities,
clock values, motor polarity, encoder direction, protocols, or physical wheel
ordering.

When evidence conflicts, record every source in `docs/unresolved.md`. Do not
silently choose a value.

## Protected paths

Treat `reference/c5-vendor/` as immutable evidence.

Do not edit, rename, reformat, regenerate, or delete vendor files. Copy only
the minimum required material into `target/c5-firmware/`, and document its
origin.

## Target project

The only long-lived firmware project belongs in `target/c5-firmware/`.

Prefer application code under an `App/` or similarly isolated directory.
Do not put substantial application logic into CubeMX-generated files.
Outside CubeMX USER CODE regions, generated files are not hand-edited.

The initial target project should contain only:

- clock and startup configuration;
- SWD;
- diagnostic UART;
- status LED if confirmed;
- fault reporting;
- explicit motor-safe initialization.

Do not add an RTOS merely because it is available. Preserve or introduce an
RTOS only when the verified requirements justify it.

## Commands and verification

Run commands from the repository root.

- Environment audit: `.\tools\doctor.ps1`
- CubeMX generation: `.\tools\generate.ps1`
- Keil build: `.\tools\build.ps1`
- Safe default verification: `.\tools\verify.ps1`
- Flashing requires the explicit confirmation switch documented by
  `.\tools\flash.ps1 -Help`.

A task is not complete because code looks correct. Record:

- commands executed;
- exit codes;
- build errors and warnings;
- produced firmware path;
- facts not yet tested on hardware.

Do not claim a hardware function works until it has passed its documented
acceptance test.

## Hardware safety

- Motor outputs must be inactive during reset and startup.
- Never flash after a failed build.
- Never drive motors during environment audit or minimal-project creation.
- Motor tests require the car to be raised so wheels cannot propel it.
- Initial motor commands must use low duty cycle and bounded duration.
- Every motion command must have an automatic stop timeout.
- Communication loss must result in motor stop.
- Do not change option bytes, readout protection, boot configuration, or
  mass-erase behavior unless a task explicitly requires it and the user has
  approved it.

## Scope discipline

Work on one vertical task at a time.

Do not perform opportunistic architecture rewrites. Do not migrate C25 code
until C5 bring-up has a stable baseline and a task explicitly requests a
specific migration.

At the end of each task, update:

- `tasks/current.md`;
- relevant files under `docs/`;
- `build/task-report.md`.

If blocked by missing evidence, finish the audit and produce precise questions
rather than guessing.
