# C5 Motion Control

## Current status

The first HAL-based motion implementation exists and builds, but it has not
been flashed or tested on the car. Firmware startup sends only the vendor's
broadcast stop command. No demo motion or host command parser is enabled.

## Vendor behavior audit

Primary source: `Carbot(C5)-STM32智能车出厂程序-250518.zip`, stored under the
ignored, read-only `reference/c5-vendor/` tree. Paths below are inside that ZIP.

| Evidence | Vendor implementation | Project conclusion |
|---|---|---|
| `USER/z_main.c:228-237` | USART3 starts at 115200 and sends `#255P1500T2000!` | Keep an active broadcast stop immediately after UART3 initialization |
| `USER/z_main.c:521-529` | `car_run(lf, rf, lr, rr)` accepts `-1000..1000` | Use logical wheel order LF, RF, LR, RR and clamp the protocol range |
| `USER/z_main.c:526-528` | Group frame uses IDs 006, 007, 008, 009 and `T0000` | Send all four wheel targets atomically as one brace-delimited frame |
| `USER/z_main.c:526-528` | Left pulse is `1500+speed`; right pulse is `1500-speed` | Default signs are `+ - + -`; physical polarity still requires a raised-wheel test |
| `USER/z_main.c:413-435` | Forward, reverse, turn and strafe combinations are explicit | Preserve those logical combinations in the mecanum mixer |
| `src/z_usart.c:109-151` | PB10/PB11, 115200, 8N1, TX and RX enabled | Current CubeMX USART3 allocation matches the vendor case |
| `src/z_usart.c:204-217` | Bytes are sent synchronously, waiting for TXE | A blocking HAL transmit is sufficient for the first version |

The vendor source also mirrors motor traffic onto USART1 for observation. The
new implementation does not do this because diagnostic framing has not yet
been designed.

## Protocol model

Single raw command:

```text
#006P1500T0000!
```

Four-wheel command:

```text
{#006P1500T0000!#007P1500T0000!#008P1500T0000!#009P1500T0000!}
```

- `P1500` is stop; the supported vendor range is `P0500..P2500`.
- ID 255 is the broadcast address used for startup and emergency stop.
- Drive commands use `T0000`, matching the vendor's continuous wheel-speed
  implementation. The physical meaning and units of nonzero `T` remain
  unresolved, so the raw single-command formatter is not treated as a
  calibrated position API.
- The application timeout is independent of `T`: it actively transmits a stop
  when a command is not refreshed before its deadline.

## Coordinate and wheel model

Logical axes are deliberately unitless until the car is calibrated:

- `vx > 0`: forward;
- `vy > 0`: strafe right;
- `wz > 0`: clockwise viewed from above.

The mixer is:

```text
LF = vx + vy + wz
RF = vx - vy - wz
LR = vx - vy + wz
RR = vx + vy - wz
```

When any magnitude exceeds the configured limit, all four outputs are scaled
by the same factor. `c5_motion_config.h` centralizes wheel IDs, polarity,
initial output limit, maximum hold time, UART timeout and stop-retry interval.
The current output limit is 700, matching the vendor demo's normal car speed;
the protocol hard limit remains 1000.

## Software layers and API

| Layer | Responsibility |
|---|---|
| `c5_motor_protocol` | Validate and encode raw single and grouped motor frames |
| `c5_mecanum` | Convert unitless `vx/vy/wz` into normalized LF/RF/LR/RR targets |
| `c5_motion` | Named movement calls, independent four-wheel command, deadline stop and fault latch |
| `c5_motor_bus_hal` | Blocking `HAL_UART_Transmit()` adapter for USART3 |

Every nonzero motion call requires a hold time from 1 to 1000 ms. The caller
must refresh a continuing command. A missed deadline sends broadcast stop.
A transport error latches `C5_MOTION_FAULT`, immediately attempts a stop and,
if that also fails, retries every 100 ms. New motion is rejected until
`C5_Motion_ClearFault()` successfully sends another stop.

`C5_Motion_CommandWheels()` supports independent LF/RF/LR/RR logical speeds.
`C5_Motion_CommandTwist()` and the named forward, backward, strafe and rotate
calls use the mixer. The main loop currently invokes only initialization and
`C5_Motion_Service()`; no autonomous movement is scheduled.

## Verification completed without hardware

- Production protocol, mixer and state-machine sources compile and run as
  host tests with MSVC `/W4 /WX`.
- Tests cover exact frame strings, vendor wheel signs, primitives,
  normalization, deadline stop, failed-stop retry and 32-bit tick wraparound.
- The complete STM32 target rebuilds with AC5.06u7 at 0 errors and 0 warnings.
- CubeMX quiet generation completes on the pinned 6.12.1 project database;
  the script persists the user's no-migration choice before and after the run.
- Keil project synchronization is deterministic and idempotent after generation.

## Required raised-chassis acceptance

Before any vehicle-level command is enabled:

1. confirm IDs 006-009 one wheel at a time;
2. confirm each positive logical speed turns its wheel in the physical forward direction;
3. verify stop pulse, DAT electrical levels and UART frame integrity;
4. measure the lowest reliable speed and choose a calibrated output limit;
5. interrupt command refresh and MCU communication to observe actual stop behavior;
6. verify forward/reverse, rotation and lateral direction at low bounded speed;
7. only then calibrate physical `vx`, `vy` and `wz` units.

The motor controller may continue its last `T0000` command if the MCU hangs or
loses power. The software deadline protects against a healthy main loop that
stops receiving commands; it is not evidence of a hardware watchdog.
