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

## M370 TTL four-wheel migration

Date: 2026-09-04

- Replaced the retired ASCII DAT motor backend with M370 binary velocity,
  immediate-stop and AA multi-motor frames.
- Bound the motor transport to USART2 PA2/PA3 at 115200 8N1. USART1 remains the
  CH340 HOST link; USART3 remains initialized but is not connected to the new
  TTL distribution board.
- Chose bring-up addresses 1/2/3/4 for LF/RF/LR/RR. These addresses and the
  initial `+ - + -` installation polarity remain hardware-unverified.
- Limited the initial software mapping to 300 RPM with 300 RPM/s acceleration.
- Added the power-off wiring, one-motor-at-a-time addressing and raised-chassis
  acceptance sequence. Gear ratio and the pusher motor are out of scope.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; M370 golden frames and motion safety tests passed |
| `tools/generate.ps1 -IocPath ...` | Exit 0; USART2/USART3 labels and USER CODE integration preserved |
| `tools/build.ps1 -ProjectPath ... -TargetName c5-firmware -Rebuild` | AC5 build completed; 0 errors, 0 warnings |
| `tools/verify.ps1` with current-worktree environment paths | Completed; doctor, both host suites, CubeMX and AC5 passed |

Program size: Code 8216, RO-data 296, RW-data 36, ZI-data 2020 bytes.

Firmware image:
`target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed, no serial port was opened and no motor command was
sent. TTL idle voltage, per-motor address/configuration, wheel polarity,
broadcast-stop behavior and all motion remain hardware-unverified.

### M370 address commissioning

Date: 2026-09-05

- Windows enumerated the WCH-Link UART as `WCH-Link SERIAL (COM11)`.
- With only one motor connected at a time, `00 15 6B` confirmed the left-front
  motor at address 1.
- Sent stored-address commands for right-front 2, left-rear 3 and right-rear 4;
  each returned `Addr AE 02 6B` and then identified itself at the new address.
- Power-cycled each changed motor and confirmed `02 15 02 6B`,
  `03 15 03 6B` and `04 15 04 6B` respectively.
- No velocity, position, torque or enable command was sent. Wheel motion was
  not requested or observed.

### WCH-Link raised-wheel motion acceptance

Date: 2026-09-05

- Connected all four motors to the shared TTL distribution board and received
  valid addressed `3A` status replies from IDs 1, 2, 3 and 4.
- Ran each wheel independently at 15 RPM for up to 5 seconds, followed by its
  addressed immediate-stop command. Command and stop acknowledgements passed;
  the user confirmed forward installation direction.
- Sent one 41-byte AA velocity frame for simultaneous four-wheel forward,
  reverse and right-strafe patterns. The user confirmed the raised-wheel
  behavior was normal.
- Stopped each motor by address after every grouped test. No ground-driving,
  left-strafe, rotation, link-loss or STM32 motor-UART test was performed.
- Replaced the firmware's broadcast stop with a 25-byte AA frame containing
  four addressed immediate-stop subcommands. Host tests and the AC5 rebuild
  passed with 0 errors and 0 warnings.

### M370 motor UART reroute

Date: 2026-09-05

- The user confirmed that H1 is the core-to-baseboard socket and that the
  baseboard has no accessible USART2 connector suitable for the installation.
- Rebound the M370 transport from USART2 PA2/PA3 to the otherwise unused
  USART3 PB10/PB11. The existing baseboard synchronous-serial connector is the
  physical connection point; USART1 remains the CH340 HOST link and the PS2
  GPIO assignment is unchanged.
- CubeMX labels remain `AUX_UART_TX/RX` on USART2 and `MOTOR_UART_TX/RX` on
  USART3. No option bytes, boot configuration or debug-pin policy changed.

| Command | Result |
|---|---|
| `tools/verify.ps1` with pinned local package paths | Completed; doctor, both host suites, CubeMX and AC5 passed |
| Keil AC5 rebuild | 0 errors, 0 warnings |

Program size: Code 8292, RO-data 296, RW-data 36, ZI-data 2020 bytes.

Firmware image:
`target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`.

No firmware was flashed and no motor command was sent. The USART3-to-M370
physical link remains hardware-unverified.

### WCH-Link firmware programming

Date: 2026-09-05

- Received explicit user authorization to flash. The core board was removed
  from the baseboard, so no motor was connected during programming.
- Detected WCH-Link as CMSIS-DAPv2, firmware 2.0.0, over SWD at 1 MHz.
- Read `DBGMCU_IDCODE=0x20036410` and a 64 KiB flash-size register, matching the
  STM32F103C8 project target.
- Programmed the addressed HEX ranges with MounRiver OpenOCD, verified them
  successfully and reset the target. No option-byte or mass-erase command was
  issued.

Firmware image: `target/c5-firmware/MDK-ARM/c5-firmware/c5-firmware.hex`

- Size: 24,306 bytes
- SHA-256: `87B79806CF73E095E8553E4A7CCAB235239E57B5C26E91F7D6E3F9B23C41ABC1`
- Result: `Programming Finished`, `Verified OK`, `Resetting Target`

The programmed firmware has not yet been accepted on the installed
USART3-to-M370 link, and no motor command was sent during this step.

### STM32 PS2 motion link observation

Date: 2026-09-05

- The user reinstalled the core board and confirmed that PS2 control drives
  the M370 wheels through the new USART3 path.
- The user reported that the resulting speed feels too slow.
- The physical gearbox ratio is 10:1. The M370 manual states that `GearRat`
  defaults to 1.00 and scales speed/position to the geared output shaft; this
  parameter has not yet been read or changed on the four addressed motors.
- No speed constant or persistent motor parameter was changed on the basis of
  this observation alone.

### M370 reduction-ratio readback

Date: 2026-09-05

- With the STM32 serial connection removed and WCH-Link UART connected to the
  shared motor board, sent addressed read-only `47` queries to IDs 1-4.
- All four returned `00 00 00 64`, confirming `GearRat=1.00` on every motor.
- The physical gearbox is 10:1, so the current 300 RPM command corresponds to
  approximately 30 RPM at the output shaft until `GearRat` is corrected.
- No persistent motor parameter and no motion command was sent.

### M370 reduction-ratio programming

Date: 2026-09-05

- With explicit user authorization, sent addressed `6A 51` commands to IDs
  1-4 with the persistent-storage flag and ratio value `00 00 03 E8` (10.00).
- Every motor acknowledged with `Addr 6A 02 6B`.
- Immediate addressed `47` readback returned `00 00 03 E8` from all four
  motors.
- No motion command was sent. Power-cycle retention remains to be checked.

After the user power-cycled and reconnected the motor bus, addressed `47`
queries again returned `00 00 03 E8` from IDs 1-4. Persistent retention of
`GearRat=10.00` is therefore confirmed. No motion command was sent during the
retention check.

### PS2 braking observation

Date: 2026-09-05

- After reduction-ratio correction, the user reported that available speed is
  sufficient but releasing the stick from high speed brakes too abruptly.
- Source inspection confirmed that valid PS2 neutral currently calls
  `C5_Motion_Stop()` and sends the M370 `FE` immediate-stop command, the same
  path used for safety stops.
- Recommended separating normal neutral deceleration from dead-man release,
  invalid/timeout frames, KEY1, mode changes and faults. No firmware change or
  flash was performed for this observation.

### PS2 controlled neutral stop and XS pusher planning

Date: 2026-09-05

- Added a normal-neutral stop path that sends four M370 `F6` zero-speed
  commands at 600 RPM/s and enters an explicit `DECELERATING` state.
- A 550 ms deadline then sends the existing addressed `FE` stop frame. Dead-man
  release, invalid/timeout PS2 data, mode changes and transport faults retain
  immediate `FE` behavior.
- Added golden-frame and state-machine tests for controlled stop, deadline stop,
  dead-man override and the unchanged fault-stop paths.
- Reviewed the user-provided XS second-generation STM32F103 HAL X-firmware
  serial example. Its UART is 115200 8N1; position command is `FD`, and
  immediate stop remains `FE 98`. The user selected the existing USART3 TTL
  network for the pusher, but address, firmware mode, power and mechanical
  limits remain unresolved.

| Command | Result |
|---|---|
| `tools/test-host.ps1` | Exit 0; controlled-stop bytes and safety state tests passed |
| `tools/verify.ps1` | Exit 0; doctor, both host suites, CubeMX generation and AC5 build passed |
| Keil AC5 rebuild | 0 errors, 0 warnings |

Program size: Code 8464, RO-data 296, RW-data 36, ZI-data 2020 bytes.

No firmware was flashed and no motor command was sent. Controlled stopping and
all XS behavior remain hardware-unverified.

### XS pusher address commissioning

Date: 2026-09-05

- Isolated the XS pusher from the STM32 and all four M370 wheel motors.
- Read-only scan found the XS at ID 2: `02 35 00 00 00 6B`.
- Sent persistent ID command `02 AE 4B 01 05 6B`; received
  `02 AE 02 6B`. ID 5 then answered and ID 2 no longer did.
- After a user-performed power cycle, ID 5 again returned
  `05 35 00 00 00 6B`; ID 2 remained silent. Persistent ID 5 is confirmed.
- Read-only configuration query `05 42 6C 6B` returned 33 bytes:
  `05 42 21 15 19 02 02 02 00 10 01 00 04 B0 0B B8 13 88 05 07 05 00 01 01 00 08 08 98 07 D0 00 08 6B`.

No enable, homing, position, velocity or stop command was sent. Pusher firmware
mode and mechanical safety parameters remain unresolved.

The user subsequently identified the pusher as Emm42 and confirmed that the
mechanism has limit protection. Limit count, contact type and whether the input
terminates at the motor driver or STM32 remain unresolved; no motion was sent.

- The user clarified that STM32 connects only shared TTL TX/RX/GND and has no
  pusher limit GPIO.
- At the retracted endpoint the display showed about -0.6 degrees. Read-only
  position query returned `05 36 01 00 00 00 73 6B`, which is negative 115
  encoder counts, approximately -0.632 degrees at 65536 counts/revolution.
- The extended display position is about 186.0 degrees, for an observed travel
  of about 186.6 degrees.
- Read-only origin query returned
  `05 22 00 00 00 1E 00 00 27 10 01 2C 03 20 00 3C 00 6B`: mode 0, direction
  0, 30 RPM, 10 s timeout, 300 RPM stall-detect speed, 800 mA, 60 ms, and
  power-on homing disabled. This is not limit-switch homing mode 3.

No homing or motion command was sent.

The user confirmed that both endpoints are mechanical hard stops, not
electrical limit switches. The planned software envelope is initially 5 to 180
degrees, leaving about 5 to 6 degrees from the observed stops. Collision homing
will not be enabled for routine operation. These limits remain hardware-
unverified, and no motion command was sent.

### Emm42 bounded motion diagnostics

Date: 2026-09-05

- With explicit user authorization for repeated tests and all wheel motors
  disconnected, attempted 50-pulse Emm position commands at 10 RPM in both
  directions. Every `FD` command acknowledged with status `02`.
- The first direction pressed slightly toward the retracted hard stop. Each
  attempt was bounded by an automatic addressed `FE` after one second.
- Cleared stall protection with `05 0E 52 6B`, re-enabled with
  `05 F3 AB 01 00 6B`, then repeated the opposite direction; no effective
  movement occurred.
- Tested both directions with the simpler `F6` velocity command at 1 RPM for
  at most 500 ms. Commands acknowledged with status `02`, but live speed stayed
  zero and position stayed near -1.1 degrees. Every attempt ended with a
  successful addressed `FE` acknowledgement.
- Read-only bus voltage was about 11.9 V. The user observed `MotType=1.8` and
  microstep 16 on the display. No persistent motor parameter was changed.

Further serial motion tests are stopped pending control/power diagnosis.

### Emm42 no-torque follow-up

Date: 2026-09-06

- Reviewed the user-provided X42S V1.0.5 manual. The two onboard buttons only
  navigate display and configuration pages; there is no panel jog function.
- The manual confirms `CR_VFOC` is FOC closed-loop mode, `0x19` is the 1.8
  degree motor type, and successful `F3 AB 01 00` enable should lock the shaft.
- The user changed the pulse-port function to off. Readback then changed from
  `P_Pul=02` to `P_Pul=00`, and the setting persisted across a power cycle.
- Repeated one bounded ID 5 velocity test at 2 RPM for 800 ms after clearing
  protection and enabling. `F3`, `F6`, and the automatic addressed `FE` all
  returned status `02`, but position was unchanged and the shaft remained
  loose. Motor status still reported enabled; stopped phase-current readback
  was only 4-7.
- No current, voltage, PID, motor-type, firmware, homing, or position parameter
  was modified. Do not integrate or raise motion limits until power, phase
  wiring, or the driver output stage explains the missing torque.

### Host status enum synchronization

Date: 2026-09-06

- Added `DECELERATING=4` to the Orange Pi `MotionState` enum and a round-trip
  protocol test so a status query during the 550 ms controlled-stop window
  cannot fail Python enum decoding.
- Commit-preparation verification ran the C host suite and RK3588 Python suite
  successfully, then completed CubeMX generation. The user requested an
  immediate push before the subsequent Keil build completed, so this final
  revision does not claim a fresh AC5 build or completed full pipeline.
