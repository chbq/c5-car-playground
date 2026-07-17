# PS2 Remote Control and SWD Sharing

## Scope

One firmware image supports two runtime modes. Reset always returns to the
debug-safe mode; no option bytes or persistent boot setting are changed.

| Mode | PA12 | PA13 | PA14 | PA15 | Vehicle behavior |
|---|---|---|---|---|---|
| Debug | Free | SWDIO | SWCLK | Free | Startup stop; no remote motion |
| PS2 control | CLK | ATT | CMD | DAT | Bounded commands from a valid controller frame |

The PS2 layer calls only the public `C5_Motion` API. It never writes motor-bus
frames directly.

## Evidence and assumptions

The C5 schematic and vendor source agree on PA12 CLK, PA13 ATT, PA14 CMD and
PA15 DAT. The vendor implementation polls nine bytes with `0x01, 0x42` and
uses analog-mode byte `0x73`; its wheel example reads the standard RY and LY
positions every 50 ms.

KEY1 is labeled PA8 by the schematic and vendor comments, but the extracted
vendor GPIO setup later configures PA8 as an output. Until measured, the new
firmware treats KEY1 polarity as a configurable assumption: input pull-up,
active low.

## Mode transitions

1. Boot in debug mode with SWD enabled and PS2 pins uninitialized.
2. Hold KEY1 for 2 seconds to request PS2 mode.
3. Send a stop, indicate the transition on PB13, disable SWJ, then initialize
   the four PS2 GPIOs.
4. Require several consecutive valid, neutral, dead-man-released frames before
   accepting control.
5. In PS2 mode, any KEY1 press immediately requests stop. Continuing to hold it
   for 2 seconds exits PS2 mode.
6. On exit, stop polling, drive the PS2 bus idle, deinitialize PA12-PA15, then
   restore SWD (`SWJ_NOJTAG`). A connected debugger may need to reconnect.
7. Reset is the unconditional recovery path back to debug mode.

An attached, actively driving ST-LINK can electrically contend with PA13/PA14
after SWD is released. Disconnect the probe before entering PS2 mode. Firmware
cannot reliably detect that cable state.

## Controls and stop conditions

- Left stick Y: longitudinal velocity `vx`.
- Left stick X: lateral velocity `vy`.
- Right stick X: yaw rate `wz`.
- L1 or R1 held: dead-man enable.
- Dead-man released, invalid frame, link timeout, KEY1 press, transition or
  motion-layer fault: stop.

Stick centers use a dead zone and the three axes are scaled to the existing
motion output limit. Every accepted command has a short hold deadline and is
refreshed only by subsequent valid frames.

## Verification boundary

Host tests can prove frame decoding, axis signs, dead zone, dead-man behavior,
arming and timeout transitions. CubeMX generation and AC5 compilation can
prove integration. They cannot prove controller electrical timing, KEY1
polarity, probe contention, wheel IDs or physical motion; those remain later
hardware acceptance items.

## Software verification result

- The decoder accepts analog IDs `0x73` and `0x79` only with reply marker
  `0x5A` and rejects malformed frames.
- Host tests cover axis signs, full-scale limiting, neutral arming, either
  shoulder dead-man, release stop, invalid-frame stop, 150 ms timeout,
  32-bit tick wraparound and both KEY1 long-press transitions.
- CubeMX regenerates PA8 as `KEY1_N` input pull-up while keeping SWD as the
  boot-time SYS debug selection.
- Keil AC5.06u7 rebuilds the complete target with zero errors and warnings.

These results verify software behavior only. KEY1 polarity, PS2 electrical
timing, receiver compatibility, LED indication, SWD reconnection and physical
vehicle motion have not been tested.
