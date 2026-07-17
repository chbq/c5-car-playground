# Hardware-in-the-loop tests

Automated HIL tests are not enabled yet. The first manual PS2 acceptance must
be recorded before a script is allowed to issue any command.

Before adding them, define:
- a machine-readable diagnostic protocol;
- bounded motor test commands;
- automatic stop behavior;
- physical preconditions such as raising the chassis;
- expected result records.

## PS2/SWD manual acceptance outline

1. Raise the chassis and initially isolate motor power.
2. Confirm reset leaves SWD available, the LED off and PS2 pins unclaimed.
3. Measure KEY1 PA8 idle/pressed levels; correct `C5_KEY1_ACTIVE_LOW` if needed.
4. Disconnect the active ST-LINK, hold KEY1 for 2 seconds and observe the
   disarmed LED blink.
5. Confirm the receiver reaches analog mode and neutral frames arm the solid
   PS2-mode LED without producing a motion frame.
6. Re-enable motor power only after the earlier single-wheel acceptance gates.
7. Hold L1 or R1 and test each axis at a bounded low limit, one axis at a time.
8. For every axis, release the shoulder button and confirm immediate stop.
9. Repeat while unplugging the receiver and with a short KEY1 press.
10. Hold KEY1 for 2 seconds to exit, then reconnect/refresh the debugger and
    confirm SWD access. Reset must also recover debug mode.

No HIL script may flash automatically or send an unbounded motor command.
