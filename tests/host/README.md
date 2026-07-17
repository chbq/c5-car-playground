# Host-side tests

`c5_motion_tests.c` compiles the production protocol, mecanum and motion-state
sources with the local Visual Studio C compiler. It covers frame encoding,
wheel-direction mapping, mecanum mixing and normalization, command expiry,
fault-stop retry and tick wraparound.

Run from the repository root:

```powershell
.\tools\test-host.ps1
```

The HAL UART adapter is excluded from host compilation and is verified by the
Keil target build. Hardware tests must never issue unbounded motor commands.
