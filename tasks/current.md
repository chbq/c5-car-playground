# Current Task - Phase 3 PS2 Remote Control

Status: Complete; software verified and partially hardware accepted

## Goal

Implement one firmware image with a debug/SWD mode and an explicitly entered
PS2 remote-control mode. Add KEY1 switching, runtime SWD release/restoration,
HAL-based PS2 I/O, mecanum stick mapping, dead-man control and host tests. Do
not flash hardware or drive motors.

## Planned work

1. [x] Reconfirm vendor PS2 pins, request bytes, analog mode and data layout.
2. [x] Document the two runtime modes, transition order, controls and test boundary.
3. [x] Add PA8 KEY1 to CubeMX while preserving SWD as the boot configuration.
4. [x] Implement PS2 protocol decoding and remote-control policy as host-testable code.
5. [x] Implement HAL GPIO bit-bang and reversible SWD/PS2 pin switching.
6. [x] Integrate KEY1 long press, neutral arming, dead-man and stop behavior.
7. [x] Run host tests, CubeMX generation and AC5 build.
8. [x] Update documentation and task report with final evidence.

## Required behavior

- Reset starts with SWD available and sends the existing broadcast stop.
- A 2-second KEY1 hold stops first, releases SWD and enters PS2 mode.
- Valid neutral frames arm the remote; L1 or R1 is the dead-man control.
- Left X/Y and right X map to `vy/vx/wz` through `C5_Motion` only.
- Invalid/lost frames, dead-man release, KEY1 press and mode exit stop motion.
- A second long press releases the PS2 pins and restores SWD.

## Constraints

- KEY1 pull-up/active-low is an explicit software assumption pending measurement.
- Disconnect an active ST-LINK before PS2 mode because PA13/PA14 become outputs.
- Reset and connect-under-reset remain recovery routes.
- No automatic flash, serial-port access or motor command is part of verification.

## Verification result

- `tools/test-host.ps1`: exit 0 under MSVC `/W4 /WX`.
- `tools/generate.ps1`: exit 0; eight App sources synchronized.
- `tools/build.ps1 -Rebuild`: exit 0; AC5.06u7, 0 errors, 0 warnings.
- `tools/verify.ps1`: exit 0 across doctor, tests, generation and build.
- Program size: Code 5448, RO-data 296, RW-data 36, ZI-data 1940 bytes.
- The automated verification did not flash hardware, open a serial port or drive motors.

## Hardware acceptance result

- The current image was flashed through the core-board SWD header and booted normally.
- Active-low KEY1 entry/exit and PB13 off/blinking/solid indication matched the design.
- The supplied 6-pin receiver link works after the controller is switched to analog mode.
- Raised-chassis and whole-vehicle tests produced correct forward/reverse, strafe and yaw directions.
- Cells at about 2.3-2.5 V each powered indicators but not motors; charging restored motion.
- Turning off the wireless controller does not invalidate receiver frames, so radio-loss safety remains unresolved.

## Next vertical task

Add a bounded USART2 host-motion protocol with explicit ownership, command
ranges and an independent stop deadline. Preserve PS2 safety behavior and keep
the wireless-controller loss issue visible until raw receiver frames are captured.
