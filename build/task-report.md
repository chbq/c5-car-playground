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

## Phase 3 hardware acceptance

Date: 2026-07-25

- The user flashed the current image through the core-board SWD header, first tested with the chassis raised, then reported normal whole-vehicle motion.
- The supplied 6-pin PS2 link, active-low KEY1 switching and PB13 mode indication matched the implementation.
- The controller must be switched to analog mode with MODE; the board then changes from blinking to solid after valid neutral frames.
- L1/R1 dead-man control and the configured forward/reverse, strafe and yaw directions drove all four wheels correctly.
- Initial weak/missing wheel motion was traced to two 14500 cells measuring about 2.3-2.5 V each; charging restored motion.
- Turning off the wireless controller leaves the receiver returning acceptable analog frames, so the existing 150 ms timeout does not prove radio-link liveness.
- SWD reconnection after PS2 exit, receiver physical-disconnect stop, raw frames on radio loss, individual motor IDs and ground-motion calibration remain open.

This documentation-only update ran no build, generation, flash or motor command.

## Repository synchronization scope

The initial Git baseline contains project-owned firmware sources, CubeMX/MDK
project files, automation scripts, prompts, tests and documentation. The
following remain local and are excluded by `.gitignore`:

- all merchant/vendor evidence under `reference/`;
- Keil build outputs including HEX, AXF, MAP, listings and object files;
- generated logs and diagnostics under `build/` except this handwritten report;
- `tools/local.env.ps1` and other machine-local state.

## Phase 4 Orange Pi to C5 motion link

Date: 2026-07-25

- Moved the Orange Pi source tree to `target/rk3588-goalkeeper/`; models,
  videos, wheels, archives, IDE/cache files and old agent metadata remain ignored.
- Selected Orange Pi `UART7_M2` (`/dev/ttyS7`) and C5 USART2 PA2/PA3 with
  crossed 3.3 V UART signals and GND only. `/dev/ttyS0` remains the board's
  1.5 Mbaud debug console and is not used.
- Added the fixed 11-byte CRC-8/ATM ARM/TWIST/STOP/QUERY command and status
  protocol with signed axes in `[-1000,1000]`.
- Added USART2 byte-interrupt receive, a four-entry event queue, main-context
  command execution/status TX, explicit ARM, 150 ms motion hold, 200 ms HOST
  disarm timeout and HOST/PS2 ownership arbitration.
- Added Python `MotionLink`, exclusive port locking, ACK/status watchdogs,
  a QUERY-by-default bounded CLI and a read-only Orange Pi environment audit.
- Removed the old football-x serial protocol. `main.py` now only observes link
  state and attempts STOP on exit; it does not ARM or command motion.
- Preserved the pre-existing local Keil schema 2.1 work copy under ignored
  `build/local-preserve/`, saved CubeMX-generated variants separately, restored
  the local copy and synchronized all 11 App source files before the final build.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; MSVC `/W4 /WX`; protocol, parser, queue/UART faults, HOST policy and PS2 arbitration passed |
| `tools/test-rk-host.ps1` | Exit 0; 7 Python tests and `compileall` passed |
| `tools/generate.ps1` | Exit 0; CubeMX completion checks passed; 11 App sources synchronized |
| `tools/build.ps1 -Rebuild` | Exit 0; AC5.06u7; 0 errors, 0 warnings |
| `tools/verify.ps1` | Exit 0 across doctor, both host suites, CubeMX generation and AC5 build |
| final build after restoring local schema 2.1 copy | Exit 0; 0 errors, 0 warnings |

Program size: Code 8352, RO-data 296, RW-data 36, ZI-data 2020 bytes.

Firmware image:
`target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed, no SSH or physical serial link was opened, and no
motor command was sent. Orange Pi environment inspection, UART7 loopback,
STM32 QUERY/ARM/STOP and raised-chassis motion/timeout/mode-interlock tests
remain hardware acceptance work requiring explicit authorization.

## Phase 4 Orange Pi audit and visual baseline sync

Date: 2026-07-26

- Established SSH key access to `orangepi@192.168.137.168` through the Windows
  mobile hotspot; the original shared WLAN allowed ARP but timed out on SSH.
- Confirmed the board is `RK3588S OPi 5 Pro`, running Orange Pi Ubuntu 22.04.5
  with kernel 6.1.43 and Python 3.10.12. This corrects the earlier 5 Plus
  assumption, so the previous pin 24/26 mapping is suspended pending a 5 Pro
  manual check.
- Confirmed `/dev/ttyS0` exists, `/dev/ttyS7` does not, and the boot image
  provides `rk3588-uart7-m2.dtbo` without enabling it. No overlay was changed.
- Copied 13 current remote source/service files and all seven RKNN models to
  ignored `build/remote-snapshot/orangepi5pro-20260726/`; source and model
  SHA-256 hashes matched the remote files. Videos, wheel, cache and IDE data
  were not copied.
- Compared the non-Git remote visual tree with the local Phase 4 tree. Imported
  the active `model_26.7.25_i8.rknn` selection, six inference workers and NMS
  threshold 0.2 while retaining MotionLink, safe exit STOP and the serial-free
  StateManager. The old `/dev/ttyS0` football-x protocol was not restored.
- Added AST-based runtime-configuration regression tests. The first run exposed
  a test helper that attempted to literal-evaluate runtime calls; the helper was
  corrected and the rerun passed.
- Confirmed the board's `yolov8` Python 3.10.20 environment imports RKNNLite,
  OpenCV 5.0.0, NumPy 2.2.6 and pyserial. Both known systemd services were
  inactive and no application process was running; no service state was changed.

| Command | Result |
|---|---|
| SSH identity/OS/serial/overlay inspection | Exit 0; read-only |
| SCP source/model backup and SHA-256 comparison | 20 files verified; zero mismatches |
| `tools/test-rk-host.ps1` via process-level execution-policy bypass | Exit 0; 10 tests and `compileall` passed |
| `tools/verify.ps1` | Exit 0; doctor, C/Python host tests, CubeMX and AC5 passed |
| final AC5 rebuild after restoring schema 2.1 Keil copy | Exit 0; 0 errors, 0 warnings; Code 8356 bytes |
| remote YOLO dependency import check | Exit 0; RKNNLite/OpenCV/NumPy/pyserial available |

上述审计与备份阶段未修改远端文件、启动配置或服务。随后仅新增独立暂存目录，
仍未覆盖原视觉工程。未连接 UART、烧录固件或发送电机命令。

### Staged Orange Pi deployment

- Committed the vertical feature as `ac9322a` (`feat: add Orange Pi host motion
  link`) after excluding all local and binary assets.
- Generated a 112,640-byte Git archive containing 24 tracked Orange Pi entries;
  no model, video, wheel, cache, IDE or agent file was present. Local and remote
  archive SHA-256 both equal
  `c46b4c415b84e3099c24eda315fe76a2710822267ba43a9ebe5cd5b6ece246bb`.
- Extracted it to
  `/home/orangepi/Desktop/c5-goalkeeper-staging-ac9322a/` and linked its
  `rknnModel` to the unchanged current model directory. The existing
  `/home/orangepi/Desktop/rk3588-yolov8/` tree was not overwritten.
- Board-side unit tests (10), `compileall` and `doctor.py` passed. Doctor confirms
  the seven models and dependencies, while correctly reporting `/dev/ttyS7`
  missing because UART7_M2 remains disabled.
- No service or `main.py` was started. The uploaded staging tree sent no serial
  command and caused no motor action.
