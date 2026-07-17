# Current Task - Phase 2 Motion Software Baseline

Status: Complete; software verified without hardware

## Goal

Use the C5 vendor case as behavioral evidence, then implement a clean HAL-based
four-wheel mecanum motion layer with bounded commands and fail-safe stop logic.
Do not flash hardware or drive motors.

## Completed work

1. [x] Audited the C5 factory source for motor protocol, IDs, wheel order, polarity, primitives, UART setup and startup stop.
2. [x] Added isolated `App/` protocol, mecanum, motion-state and HAL UART3 layers.
3. [x] Added independent LF/RF/LR/RR speeds and unitless `vx/vy/wz` APIs.
4. [x] Added forward, backward, strafe, rotate and explicit stop calls.
5. [x] Added mandatory 1-1000 ms command expiry, active stop, fault latch and stop retry.
6. [x] Centralized unverified IDs, wheel signs, output limit and timing parameters.
7. [x] Added deterministic CubeMX-to-Keil App source synchronization.
8. [x] Compiled and ran host tests with MSVC `/W4 /WX`.
9. [x] Rebuilt the STM32 target with AC5.06u7: 0 errors, 0 warnings.
10. [x] Documented evidence, architecture, API and raised-chassis acceptance requirements.
11. [x] Repeated CubeMX quiet generation with the 6.12.1 database and preserved all USER CODE/App integration.
12. [x] Ran the full no-flash verification pipeline: doctor, host tests, generation and AC5 build all passed.

## Current firmware behavior

- USART3 is initialized by generated HAL code.
- Startup immediately sends `#255P1500T0000!`.
- The main loop services motion expiry and fault-stop retries.
- No movement command is issued automatically.
- No upstream serial command parser is enabled.

## CubeMX automation resolution

The first quiet runs stalled because `.ioc` retained
`ProjectManager.AskForMigrate=true`; the GUI normally answers this with the
"continue as 6.12" dialog, but quiet mode cannot. `generate.ps1` now persists
the already chosen 6.12.1 no-migration setting before and after generation,
requires CubeMX `OK`/`Bye bye` markers, checks that the MDK project was
refreshed, and then synchronizes the App group. Repeated unattended generation
now exits normally.

## Next vertical task

Perform flash/boot and raised-chassis single-wheel acceptance as a separately
authorized task. Only after wheel IDs,
physical signs and communication-loss behavior pass should a host command
protocol be connected to the movement API.
