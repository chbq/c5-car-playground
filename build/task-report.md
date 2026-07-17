# Task Report - Hardware, Toolchain and Generated Baseline

Date: 2026-07-15

## Outcome

- Organized `docs/` as a compact linked hardware wiki.
- Recorded the system requirements, board architecture, H1 map, pin/peripheral budget, evidence inventory and unresolved checks.
- Initially classified the 8 MHz HSE value as source-derived; the user subsequently accepted it as the project input without further physical verification.
- Initialized an empty Git repository on branch `main`.
- Left all files unstaged and uncommitted.
- Clarified that `MANIFEST.json` is the original scaffold checksum snapshot, not a live post-adaptation manifest.

## Commands and results

| Operation | Result |
|---|---|
| Bounded repository inventory with `rg --files` and PowerShell counts | Exit 0 |
| Vendor PDF metadata/text inspection with bundled `pypdf` | Exit 0 |
| Core/base schematic rendering for visual pin verification | Exit 0; temporary previews removed after use |
| Read-only ZIP inventory and targeted vendor-source extraction with `tar` | Exit 0 |
| Physical-photo metadata and visual inspection | Completed; crystal marking remained unreadable |
| `git init -b main` | Exit 0 |

## Explicitly not run

- `tools/doctor.ps1`
- `tools/generate.ps1`
- `tools/build.ps1`
- `tools/verify.ps1`
- `tools/flash.ps1`
- CubeMX, Keil, compiler, programmer or motor-control commands

## Build and firmware

- Build errors: not applicable; no build was run.
- Build warnings: not applicable; no build was run.
- Firmware output path: none.

## Hardware not tested

- Physical crystal marking and PCB revision silks; these are now deferred rather than project-generation blockers.
- H1 pin-1 orientation and continuity.
- SWD connectivity and NRST access.
- Power-rail voltages.
- USART electrical behavior and CH340 enumeration.
- DAT idle voltage, waveform and collision behavior.
- Physical motor IDs, wheel mapping, command timing and communication-loss stop.
- No board was flashed and no motor was driven.

## Toolchain audit update

- Created ignored `tools/local.env.ps1` with current machine paths.
- Extended doctor to report tool versions, compiler versions, CubeF1 repositories and Keil DFP installations.
- Pinned STM32CubeF1 1.8.7 and ARM Compiler 5.06u7 for the first baseline; retained ARM Compiler 6.19 for later compatibility builds.
- Added an idempotent official-pack installer and installed Keil STM32F1xx DFP 2.4.1.
- Verified that the installed DFP contains STM32F103C8.
- Final doctor run exited 0 and both JSON and Markdown reports were validated.

| Toolchain operation | Result |
|---|---|
| PowerShell syntax parse for modified scripts | Exit 0; zero parse errors |
| Installer preview with `-WhatIf` | Exit 0 |
| First installer invocation with incorrectly forwarded `-Confirm:$false` | Exit 1 before download or installation; command corrected |
| DFP 2.4.1 download and installation | Exit 0 |
| Idempotent installer re-run | Exit 0; reported already installed |
| First enhanced doctor run | Exit 0; exposed a Markdown escaping defect |
| Doctor report escaping fix and final re-run | Exit 0 |

The DFP archive SHA-256 is `807EA15DA5B172B916BBC47B2B87F1E621240AD208D38E82A417A2EF8191E9D1`.

## Phase 0 status

Phase 0 is complete. Physical H1/SWD wiring may be verified when the cable is made; it does not block project generation.

## Phase 1 CubeMX and Keil baseline

- Created `target/c5-firmware/c5-firmware.ioc` for STM32F103C8T6.
- Generated the CubeF1 1.8.7 HAL and MDK-ARM V5 project.
- Configured HSE 8 MHz / SYSCLK 72 MHz, SWD, three 115200 UARTs and PB13 LED off at startup.
- Confirmed the generated code contains no UART transmit call or motor command.
- Rebuilt with ARM Compiler 5.06 update 7 build 960.

| Command | Result |
|---|---|
| `tools/generate.ps1` | Exit 0; MDK project generated |
| `tools/build.ps1 -Rebuild` | Exit 0; 0 errors, 0 warnings |

Program size: Code 2024, RO-data 276, RW-data 16, ZI-data 1848 bytes.

Firmware image: `target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed, no serial link was opened and no motor command was sent.

Automation issues found and corrected during the first run:

- `generate.ps1` originally evaluated the local `.ioc` path before loading
  `local.env.ps1`; the load order was fixed.
- the local CubeMX update retained an obsolete `userauth.jar`, causing
  `NoClassDefFoundError: BrowserView`; it was renamed to `.disabled` and
  generation then completed.
- CubeMX can return process success even when no IDE project was produced;
  `generate.ps1` now requires the expected `.uvprojx` output.
- PowerShell did not wait for the GUI-subsystem `UV4.exe`; `build.ps1` now waits
  for completion and validates the final Keil error/warning summary and HEX file.

## Phase 2 motion software baseline

- Audited the C5 factory source for USART3 setup, broadcast stop, group framing,
  motor IDs, left/right pulse signs and six basic vehicle movements.
- Implemented production protocol encoding, mecanum mixing, independent wheel
  commands, named movements, deadline stop, UART-fault latch and stop retry.
- Added a blocking HAL UART3 adapter; no RTOS, interrupt TX or DMA was added.
- Startup now sends only `#255P1500T0000!`; no motion is scheduled.
- Added deterministic, idempotent synchronization of `App/Src/*.c` into the
  CubeMX-generated Keil project.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; MSVC `/W4 /WX`; `c5_motion_tests: PASS` |
| `tools/build.ps1 -Rebuild` | Exit 0; AC5.06u7; 0 errors, 0 warnings |
| `tools/verify.ps1 -SkipGenerate` | Exit 0; doctor, host tests and Keil build all passed; no flash |
| `tools/sync-keil-project.ps1` repeated twice | Exit 0; identical SHA-256 after second run |
| `tools/generate.ps1` attempt 1 | External runner timed out at 120 s; CubeMX 6.18.0-RC3 remained at DB.6.0.121 load |
| `tools/generate.ps1` attempt 2 | Reproduced the same stall beyond normal startup time; process terminated and log retained |
| `tools/generate.ps1` after migration-prompt fix | Exit 0 twice; `OK` / `Bye bye`; USER CODE and App project group preserved |
| `tools/verify.ps1` full pipeline | Exit 0; doctor, host tests, CubeMX generation and AC5 build passed; no flash |

Program size after motion integration: Code 2996, RO-data 284, RW-data 28,
ZI-data 1876 bytes.

Firmware image: `target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

Root cause of the quiet-mode stall was the interactive
`ProjectManager.AskForMigrate=true` flag. The user had already selected
"continue as 6.12" in the GUI; `generate.ps1` now persists that choice for
unattended runs and validates both CubeMX completion markers and MDK project
refresh time. The regeneration gate is complete.

No firmware was flashed, no serial port was opened and no motor was driven.

## Phase 3 PS2/SWD dual-mode remote control

Date: 2026-07-17

- Added a standard nine-byte PS2 decoder for analog IDs `0x73` and `0x79`.
- Added host-testable neutral arming, L1/R1 dead-man, mecanum stick mapping,
  invalid-frame stop and 150 ms link timeout with tick-wrap handling.
- Added a KEY1 state machine: 30 ms debounce, immediate stop on a PS2-mode
  press, and 2-second long-press entry/exit.
- Added HAL GPIO bit-bang on PA12 CLK, PA13 ATT, PA14 CMD and PA15 DAT using
  DWT cycle timing. Entry disables SWJ only after an explicit request; exit
  idles and deinitializes the PS2 pins before restoring SWD.
- Added PA8 `KEY1_N` input pull-up to CubeMX. Active-low polarity remains an
  explicit unverified configuration assumption.
- Added PB13 mode feedback: off in debug mode, blinking while PS2 is disarmed,
  solid while the remote is ready or active.
- Refreshed the root overview, firmware README, hardware wiki, acceptance gates
  and manual HIL outline.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; MSVC `/W4 /WX`; `c5_motion_tests: PASS` |
| `tools/generate.ps1` | Exit 0; CubeMX completion markers present; 8 App sources synchronized |
| `tools/build.ps1 -Rebuild` | Exit 0; AC5.06u7; 0 errors, 0 warnings |
| `tools/verify.ps1` | Exit 0; doctor, host tests, CubeMX generation and Keil build all passed |

Program size: Code 5448, RO-data 296, RW-data 36, ZI-data 1940 bytes.

Firmware image: `target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed, no serial port was opened and no motor command was
sent. KEY1 polarity, controller timing/compatibility, LED behavior, SWD
reconnection and every physical motion behavior remain unverified hardware
acceptance items.

## Repository synchronization scope

The initial Git baseline contains project-owned firmware sources, CubeMX/MDK
project files, automation scripts, prompts, tests and documentation. The
following remain local and are excluded by `.gitignore`:

- all merchant/vendor evidence under `reference/`;
- Keil build outputs including HEX, AXF, MAP, listings and object files;
- generated logs and diagnostics under `build/` except this handwritten report;
- `tools/local.env.ps1` and other machine-local state.
