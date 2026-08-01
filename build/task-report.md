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

## Phase 4 HOST transport migration to USB/CH340

Date: 2026-07-26

- Replaced the unresolved Orange Pi UART7_M2/40-pin route with the core-board
  USB CH340 path. STM32 HOST RX/TX now uses USART1 PA10/PA9; USART2 PA2/PA3
  remains initialized as an uncommitted 3.3 V expansion UART without RX IRQ.
- Kept the fixed frame protocol, ARM gate, timeouts, fault stops and HOST/PS2
  arbitration unchanged. UART callbacks now match the adapter's bound handle.
- Added Orange Pi CH340 discovery with `C5_HOST_PORT`, `/dev/c5-host`, stable
  `/dev/serial/by-id` and single-`ttyUSB` fallback selection.
- Changed pyserial startup to configure DTR/RTS inactive before opening and to
  request OS-level exclusive access. The core-board auto-download transient
  remains a physical acceptance item.
- Updated the doctor, CLI, unit tests, CubeMX pin labels/NVIC configuration,
  wiring guide, pin budget, acceptance gates and current task.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; `c5_motion_tests: PASS` |
| `tools/test-rk-host.ps1` | Exit 0; 15 Python tests and `compileall` passed |
| `tools/verify.ps1` | Exit 0; doctor, both host suites, CubeMX generation and AC5 rebuild passed |

Program size: Code 8340, RO-data 296, RW-data 36, ZI-data 2020 bytes.

Firmware image:
`target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed, no serial device was opened and no motor command was
sent. CH340 enumeration/permissions, repeated DTR/RTS open-close behavior,
STM32 QUERY/ARM/STOP and raised-chassis motion tests remain hardware work.

### USB/CH340 physical protocol acceptance

- The user flashed the USART1 HOST firmware and connected the core-board USB
  port to the Orange Pi 5 Pro.
- USB enumeration reported QinHeng `1a86:7523`. The kernel initially created
  `ttyUSB0`, but active `brltty-udev.service` claimed the interface and detached
  `ch341`. The service was stopped temporarily and `ch341` rebound; it was not
  disabled, masked or uninstalled.
- The stable path is
  `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`; the `orangepi` user has
  `dialout` access. Both application services remained inactive.
- Deployed the uncommitted working tree to the isolated directory
  `/home/orangepi/Desktop/c5-goalkeeper-staging-ch340-20260726/`; the original
  visual project and earlier staging tree were not overwritten. The 114,176
  byte archive SHA-256 matched locally and remotely:
  `c4352da4aef0b7492737b039982cef4947afe930d3af7053a8c518becd443d5e`.
- Board-side 15 tests, `compileall` and the updated read-only doctor passed.
- QUERY and STOP returned `OK/HOST/DISARMED/STOPPED/errors=0`.
- Twenty independent open/QUERY/close cycles all passed, with no observed
  Bootloader lock-up. Zero-speed ARM/TWIST stayed stopped and STOP disarmed.
- ARM without refresh automatically returned to DISARMED/STOPPED after 350 ms.
- A corrupted CRC produced `BAD_CRC`, incremented the error count to one and
  stopped/disarmed; the next legal QUERY returned OK with the link usable.

- With explicit user authorization and the wheel set raised, `vx=100`,
  `vy=100` and `wz=100` each ran for 0.5 seconds with the expected physical
  direction and returned to DISARMED/STOPPED with zero errors.
- Two diagonal mixes passed: `vx=50,vy=50` drove only left-front/right-rear;
  `vx=50,vy=-50` drove only right-front/left-rear.
- A visible watchdog test ran `vx=50` and killed the sender with `SIGKILL`
  after 1.2 seconds, bypassing the Python `finally` STOP. The wheels visibly
  stopped and a later QUERY returned `OK/HOST/DISARMED/STOPPED/errors=0`.

Persistent `brltty-udev` handling, reboot verification, physical USB unplug
and HOST/PS2 arbitration remain open. No ground-driving test was performed.

## Phase 5A ball-pixel yaw loop

Date: 2026-07-26

- Added a pure Python pixel controller with confidence gating, center deadband,
  bounded proportional yaw, slew limiting and zero-crossing direction changes.
- Added a 20 Hz session that requires three consecutive valid targets before
  ARM, sends zero immediately on target loss, requires confirmation after
  reacquisition and stops/disarms after 0.5 seconds without a target.
- Refactored `main.py` for explicit `idle`, `inference` and
  `ball-yaw-test` modes. The test defaults to dry-run; only `--execute` can
  ARM, and its duration is capped at 30 seconds.
- Deployed to the isolated directory
  `/home/orangepi/Desktop/c5-goalkeeper-staging-phase5a-20260726/`; the visual
  baseline and earlier staging directories were not overwritten.
- Masked `brltty-udev.service` without uninstalling the package. After reboot,
  it remained masked/inactive and CH340 attached normally as `ttyUSB0`.
- Board doctor and QUERY passed after reboot. A 3-second headless dry-run
  opened the 1280x720@120 camera, ran six RKNN workers at about 56 FPS and
  reported `NO_TARGET`, `wz=0`, `armed=False`; the post-run status was
  `HOST/DISARMED/STOPPED/errors=0`.

| Command | Result |
|---|---|
| `tools/test-rk-host.ps1` | Exit 0; 28 tests and `compileall` passed |
| `tools/verify.ps1` | Exit 0; doctor, C/Python tests, CubeMX and AC5 passed |
| AC5 build | 0 errors, 0 warnings; Code 8340, RO 296, RW 36, ZI 2020 |
| board unit tests and `compileall` | Exit 0; 28 tests passed |
| rebooted board doctor and QUERY | CH340 OK; DISARMED/STOPPED/errors=0 |
| `main.py --headless --mode ball-yaw-test --duration 3` | Exit 0; dry-run only |

Firmware image:
`target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

The initial deployment and dry-run did not flash firmware, ARM or move a
motor. Subsequent raised-chassis tests were explicitly authorized:

- Ball-present dry-run confirmed negative/zero/positive yaw across the image.
- Initial motion attempts exposed a discharged 4 V motor pack; charging
  restored motion.
- Intermittent detections exposed premature target-loss exit. An explicit
  bounded raised-test mode now keeps ARM until the total duration, sends zero
  during target loss and requires three valid cycles before resuming motion.
- A real watchdog regression was found when paused zero commands stopped
  refreshing. The firmware correctly disarmed after 200 ms; the application
  then reported `HOST is not armed`. Continuous 20 Hz zero refresh and a
  regression test fixed it.
- Two final 30-second tests completed without early exit. Actual sent yaw
  covered positive, zero and negative values; target loss held
  `armed=True/sent=0`, detection recovery resumed motion, and only duration
  expiry issued STOP.
- Final QUERY returned `HOST/DISARMED/STOPPED/errors=0`; the user confirmed
  correct right turn, center stop, left turn and recovery after target loss.
- The final full-verify retry stalled inside CubeMX after its third-party
  package integrity scan and produced no completion markers. The launched
  `javaw` process was stopped after several minutes; `target/c5-firmware/`
  had no Git drift. A direct AC5 rebuild and
  `verify.ps1 -SkipGenerate` then passed with 0 errors and 0 warnings. The
  earlier Phase 5A full verify, including CubeMX generation, had already
  passed; no STM32 source or `.ioc` changed afterward.

No firmware was reflashed and no ground-driving test was performed.
HOST/PS2 arbitration and an explicit Ctrl+C stop test remain open.

### Ground-test presets

- Added repeatable `ground-check` and `ground-demo` profiles. They bound
  duration, yaw output, gain, deadband, confidence and target-loss handling.
- Profiles do not imply `--execute`; the same profile can first run dry.
  Holding ARM across target loss is enabled only with explicit execution.
- Local and board-side suites passed 29 tests. Board-side `main.py --help`
  passed under the actual `yolov8` Conda environment and exposed both
  profiles plus the separate `--execute` gate.
- No serial command, firmware flash or ground motion was performed while
  adding or verifying the profiles.

On 2026-08-01, after the motor battery was recharged, the user explicitly
authorized and confirmed both the 15-second `ground-check` and a complete
30-second `ground-demo` on the ground. The second demo covered positive and
negative yaw, center stop, target loss and reacquisition, exited normally at
the duration limit, and ended at `HOST/DISARMED/STOPPED/errors=0`.

## Phase 5B ball-pixel lateral loop

Date: 2026-08-01

- Added `BallStrafeController` with normalized horizontal error, confidence
  gating, a 0.10 deadband, `vy=250..800`, gain 1000, 120-unit slew limit and
  zero-crossing direction reversal.
- Added `BallStrafeSession` at 20 Hz. It requires three valid cycles before
  ARM and sends only `vx=0, vy, wz=0`; target loss immediately sends zero and
  explicit execution holds zero until the bounded 30-second session ends.
- Added `ball-strafe-test` to `main.py`. It remains dry-run unless the separate
  `--execute` gate is present. No STM32 source or protocol change is required.
- Local and board-side RK host tests and `compileall` passed 39 tests. The
  user explicitly allowed the first physical run without a separate dry-run.

The first explicitly authorized 30-second physical run completed and ended at
`HOST/DISARMED/STOPPED/errors=0`, but the user observed that the car moved away
from the ball. The C5 default was therefore corrected from
`lateral_sign=+1` to `-1`; physical acceptance remains pending a rerun.

The corrected 30-second rerun completed normally. Sent lateral output covered
approximately `vy=-720..+528`; center, missing and low-confidence detections
sent zero. The final QUERY returned `HOST/DISARMED/STOPPED/errors=0`. The user
confirmed that the vehicle translated toward the ball and did not turn its
heading, which is expected because Phase 5B fixes `wz=0`. Phase 5B physical
acceptance passed.

## Phase 5C combined ball-follow loop

Date: 2026-08-01

- Added `BallFollowController` and `BallFollowSession` to combine the verified
  C5 lateral sign with the verified yaw sign while fixing `vx=0`.
- Defaults are `vy=250..800` and `wz=40..180`; their maximum sum is 980, so
  the STM32 mecanum mixer does not normalize the command.
- Added the dry-by-default `ball-follow-test` mode with the same 20 Hz,
  three-cycle acquire, target-loss zero refresh, bounded duration and global
  STOP behavior.
- Local RK host tests and `compileall` passed 49 tests. Board and physical
  combined-motion acceptance remain pending.

Board-side 49 tests, `compileall`, CLI help and a 5-second dry-run passed. An
explicitly authorized 30-second physical test completed and ended at
`HOST/DISARMED/STOPPED/errors=0`, with approximately `vy=-720..+706` and
`wz=-120..+141`. Safety behavior passed, but the user observed the car moving
away from a ball on the right. The log showed yaw rapidly centering the ball
in the image, which also removed the lateral command. One horizontal image
error cannot independently determine heading and lateral position, so this
combined controller failed behavioral acceptance and is not a keeper baseline.

## Phase 5C revised ball-pursuit loop

Date: 2026-08-01

- Replaced the rejected `vy+wz` behavior with `vx+wz`; pursuit fixes `vy=0`.
- Extended `FootballInfo` with bounding-box width and height while preserving
  the original `(x, y, confidence)` return used by the display loop.
- Horizontal image error drives yaw. Forward motion is gated off beyond 0.35
  normalized error, decreases as box-height ratio grows from 0.20 to 0.45, and
  stops immediately at the near threshold.
- Defaults are `vx=250..800` and `wz=40..180`; the maximum sum remains 980.
- Local Python tests passed 54 cases and `compileall` passed. No firmware was
  changed or flashed, and no motor command was sent at this local checkpoint.

The source-only 41 KB deployment was installed at
`/home/orangepi/Desktop/c5-goalkeeper-staging-phase5c-pursuit-20260801` without
overwriting the previous staging tree. Board-side 54 tests, `compileall`, CLI
help and a 5-second dry-run passed. The dry-run observed a box-height ratio near
0.25 and produced targets around `vx=+375,wz=-40`, while remaining
`sent=(-)/armed=False`. A final QUERY returned
`HOST/DISARMED/STOPPED/errors=0`. No motor command was sent; physical acceptance
and distance-threshold calibration remain pending.

After explicit authorization, a 30-second ground run completed at the normal
deadline. Logs exercised turn-only `ALIGNING`, forward `APPROACHING`, near-stop
`NEAR`, and target-loss zero refresh; the final QUERY returned
`HOST/DISARMED/STOPPED/errors=0`. The user observed that yaw turned toward the
ball, but the vehicle consistently translated toward the left. The pursuit
mode always sent `vy=0`, so behavioral acceptance failed pending an isolated
pure-`vx` ground test.

The user then clarified the missing camera extrinsic: the camera is mounted on
the vehicle's right side, and positive `vx` translates the camera toward image
left. The positive-only `vx` design was therefore incorrect for image-space
tracking. Phase 5C now maps image-left to positive `vx`, image-right to negative
`vx`, center to zero, and keeps `vy=0`; yaw mapping is unchanged. Sign symmetry,
center stop, zero-crossing reversal and session safety passed all 54 local tests
and `compileall`. Board deployment and physical retest remain pending.

The user further defined the camera-frame axes: `vx` is camera left/right and
`vy` is camera forward/back. The controller now maps horizontal image error to
signed `vx`, apparent-size error around a 0.35 box-height ratio to signed `vy`,
and horizontal error to `wz`. It proportionally limits the three-axis absolute
sum to 1000 before transport. A new full-rate CSV logger records detection box,
confidence, image and distance errors, target/sent axes, session state and IMU
attitude on every 20 Hz control tick. All 57 local tests and `compileall` pass;
no motor command was sent.

The source-only revision was deployed at
`/home/orangepi/Desktop/c5-goalkeeper-staging-phase5c-camera-axes-20260801`.
Board-side 57 tests, `compileall`, CLI help and a 5-second dry-run passed. The
observed ball was inside both deadbands (`x_error` about -0.048, box ratio about
0.311), so all target axes stayed zero. The dry-run produced a 60-line CSV with
empty sent-axis fields and `armed=0`; final QUERY was
`HOST/DISARMED/STOPPED/errors=0`. At this checkpoint, physical retest remained
pending.

After explicit authorization, the corrected camera-frame controller completed
a 30-second ground test. The user confirmed that physical behavior was correct.
The 514-row CSV covered negative/zero/positive sent values for all axes:
`vx=108/266/138`, `vy=131/288/93`, and `wz=138/266/108`. Control intervals were
50.0 ms minimum, 58.3 ms average, 88.6 ms p95 and 116.7 ms maximum; none crossed
the 200 ms STM32 watchdog. All 21 no-target and 2 low-confidence rows sent zero.
The session stopped at its deadline and final QUERY returned
`HOST/DISARMED/STOPPED/errors=0`. Phase 5C physical acceptance passed.

## Phase 5D and Phase 6 design checkpoint

Date: 2026-08-01

- Recorded Phase 5D as a narrow-field-of-view protection layer: yaw receives
  priority near image edges, translation is reduced, filtered image velocity
  supports bounded prediction, and hysteresis prevents mode chatter.
- Target loss remains a zero-motion wait rather than terminating the session;
  stale observations must not cause unbounded translation or search rotation.
- Recorded the Phase 6 field-frame goalkeeper architecture, localization
  inputs, threat/intercept state machine and staged acceptance path in
  `docs/goalkeeper-behavior.md`.
- The current model exposes a `goal` class, but the present test area has no
  goal frame. Goal detection and own/opponent identification remain physically
  unverified.
- This checkpoint changes documentation only. No code, deployment, firmware,
  flash or motor command was executed.

## Phase 5D narrow-FOV protection implementation

Date: 2026-08-01

- Added the dry-by-default `ball-fov-test` mode without changing the accepted
  Phase 5C `ball-follow-test` defaults.
- Added filtered horizontal error/rate, 150 ms prediction, CENTER/TRACK/EDGE
  zones and 0.55/0.30 hysteresis.
- EDGE limits translation to 25% and reserves command budget for yaw first;
  default yaw is 60..260 at gain 320.
- A previously armed session may use a recent reliable observation for at
  most 150 ms of yaw-only prediction. It never translates or first-arms from
  predicted data, then returns to zero and requires three fresh detections.
- CSV now records filtered/rate/predicted error, zone, target age, lost frames
  and whether a command is prediction-only.
- Full local RK validation passed 65 tests and `compileall`. No STM32 source,
  firmware generation, build, flash, deployment or motor command was used at
  this checkpoint.

The source-only 47 KB archive was deployed to
`/home/orangepi/Desktop/c5-goalkeeper-staging-phase5d-fov-20260801`; its local
and remote SHA-256 matched. Board-side 65 tests, `compileall` and CLI help
passed. An initial combined shell check timed out only because an unquoted
`grep -E` pattern became a pipeline; the exact leftover shell/grep PIDs were
inspected and terminated before continuing.

A 5-second no-ball dry-run completed at about 56 FPS and wrote a 58-line CSV
with the Phase 5D telemetry fields. It remained dry and unarmed throughout.
The final QUERY returned `HOST/DISARMED/STOPPED/errors=0`. Physical edge,
prediction and reacquisition behavior remains unverified; no motor command or
firmware operation was performed.
