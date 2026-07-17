# Host-side tests

`c5_motion_tests.c` compiles the production protocol, mecanum and motion-state
sources with the local Visual Studio C compiler. It covers motor framing,
wheel-direction mapping, mecanum mixing, command expiry, fault-stop retry,
tick wraparound, PS2 decoding and axis signs, neutral arming, dead-man control,
link timeout and KEY1 long-press mode transitions.

Run from the repository root:

```powershell
.\tools\test-host.ps1
```

The HAL UART adapter is excluded from host compilation and is verified by the
Keil target build. Hardware tests must never issue unbounded motor commands.
