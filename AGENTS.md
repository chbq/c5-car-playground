# Repository Instructions

## Mission and scope

Build and maintain the clean STM32CubeMX + Keil HAL firmware for the C5
four-wheel mecanum car.

- C5 is the only active hardware target.
- C25 may be used only after the C5 baseline is stable and a task explicitly
  requests a specific algorithm or behavior reference.
- The current firmware already contains the generated baseline, motor
  protocol, mecanum motion layer, fail-safe stop logic and PS2/SWD dual mode.
  These are software-verified but remain hardware-unverified until their
  acceptance gates pass.

## Evidence and assumptions

Hardware facts must come from one or more of:

1. schematics and vendor documentation in `reference/c5-vendor/`;
2. vendor `.ioc` files, if any;
3. vendor Keil projects and startup/linker configuration;
4. mutually consistent vendor example code;
5. measurements or observations explicitly recorded by the user.

Classify important values as one of:

- **Confirmed**: explicit hardware documentation or mutually consistent
  evidence;
- **User-observed**: a physical observation supplied by the user;
- **Accepted design input**: an assumption the user explicitly accepted so
  development can proceed;
- **Software-only**: implemented and compiled/tested, but not verified on the
  car;
- **Unresolved**: missing, conflicting or insufficient evidence.

Never invent MCU variants, pins, timers, channels, interrupt priorities,
clocks, motor polarity, encoder direction, protocols or wheel order. A user
may explicitly accept a working assumption; centralize it in configuration,
document it, and keep its hardware status unverified.

Record conflicting evidence in `docs/unresolved.md`; do not silently choose a
winner.

## Protected and generated paths

Treat `reference/c5-vendor/` as immutable evidence. Do not edit, rename,
reformat, regenerate or delete vendor files. Copy only the minimum material
required by an explicit task, and document its origin.

The only long-lived firmware project is `target/c5-firmware/`.

- Keep application logic under `target/c5-firmware/App/`.
- Keep substantial logic out of CubeMX-generated files.
- Edit generated files only inside CubeMX `USER CODE` regions.
- Change pin, clock and peripheral ownership in the `.ioc`, then regenerate.
- Do not add an RTOS unless verified requirements justify it.
- Do not copy legacy Standard Peripheral Library code into the HAL target.

## Code and documentation style

- Project documentation under `README.md` and `docs/` uses compact Chinese.
- C source, headers and Doxygen comments under `App/` stay ASCII English for
  MSVC code-page and ARM Compiler 5 compatibility.
- Document public APIs at declarations in `App/Inc` with concise Doxygen
  `@brief`, `@param`, return values, units, ranges, blocking behavior and safety
  effects where relevant.
- Add short comments to non-obvious internal state, protocol and safety logic.
  Do not add template comments to trivial getters or obvious helpers.
- Keep configurable, hardware-unverified values in focused configuration
  headers rather than scattering literals through the implementation.

## Commands and verification

Run commands from the repository root:

- environment audit: `.\tools\doctor.ps1`;
- host tests: `.\tools\test-host.ps1`;
- CubeMX generation: `.\tools\generate.ps1`;
- Keil rebuild: `.\tools\build.ps1 -Rebuild`;
- safe full pipeline: `.\tools\verify.ps1`;
- flashing: use the explicit confirmation switch documented by
  `.\tools\flash.ps1 -Help`.

Match verification to the change:

| Change | Minimum verification |
|---|---|
| `App` C/header logic | host tests and AC5 rebuild |
| `.ioc`, generated integration or Keil project | CubeMX generation and AC5 rebuild; also run host tests when `App` is affected |
| automation scripts | syntax/parse check plus the affected command or a documented safe dry run |
| documentation only | `git diff --check` and local-link/consistency checks; no firmware build required |
| vertical milestone or release candidate | full `.\tools\verify.ps1` |

Do not weaken warnings-as-errors or skip a relevant check merely to make a
change pass. Save verbose logs under ignored `build/` and report bounded
summaries.

For vertical milestones, record commands, exit codes, errors/warnings, firmware
path and hardware-unverified facts. Never claim hardware behavior from a host
test or successful build.

## Hardware safety

- Reset and startup must send no motion command and must actively request stop.
- Never flash after a failed build.
- Never drive motors during environment audit, generation or build.
- Raise the chassis before motor tests.
- Initial motor tests must be low speed, bounded and one behavior at a time.
- Every motion command requires an automatic stop deadline.
- Communication loss or invalid control data must result in stop.
- Flashing and motor motion require explicit user authorization; neither is
  part of the default verification pipeline.
- Do not change option bytes, readout protection, boot configuration or
  mass-erase behavior without a task that explicitly requires it and user
  approval.

For PS2/SWD sharing:

- boot with SWD enabled;
- disconnect an actively driving ST-LINK before assigning PA13/PA14 to PS2;
- stop first, then disable SWJ and initialize PS2 GPIO;
- on exit, idle and deinitialize PS2 GPIO before restoring SWD;
- reset remains the unconditional recovery path;
- do not use option bytes to persist the PS2 pin mode.

## Scope, records and Git

Work on one vertical task at a time. Do not perform opportunistic architecture
rewrites or unrelated migration.

Update `tasks/current.md`, relevant `docs/` pages and `build/task-report.md`
when a vertical feature, hardware conclusion or formal verification milestone
changes. Minor wording, translation, comment-only and formatting tasks do not
need to rewrite all three records unless they change a fact or acceptance
status.

Commit only project-owned source, documentation, tests, automation and required
CubeMX/Keil metadata. Keep vendor evidence, machine-local configuration, logs
and build products untracked.

If evidence is missing, complete all safe in-scope work, record the precise
unknown and ask a focused question instead of guessing.
