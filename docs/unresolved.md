# C5 Unresolved Questions

| Priority | Question | Current evidence | Affected work | Safe action | Required check |
|---|---|---|---|---|---|
| Deferred | What are the exact physical core/base board revisions? | PDF title blocks are core V3 and base V3.4; current photo does not make both silk revisions readable | Applicability of all schematic facts | Use the vendor document revisions unless hardware behavior disagrees | Photograph both PCB revision silks if needed |
| Deferred | Can SWD be used reliably from H1, and where is NRST accessible? | H1 exposes PA13/PA14, 3.3 V and GND; user observes accessible female headers; NRST is absent from H1 | Debug cable and connect-under-reset | Preserve SWD and do not enable PS2 | Verify while making the actual cable |
| High before motor power | What are DAT idle level, voltage and transceiver device details? | Base schematic shows a single-wire conversion circuit but gate part numbers/electrical behavior are incomplete | USART electrical safety and collision handling | Do not connect an external push-pull driver to DAT | Measure idle voltage and capture a known transaction |
| High before motion | Are physical motor IDs and wheel locations actually 006/007/008/009? | Vendor configuration manual defines these IDs and positions | Correct wheel mapping | No motion commands | Read IDs or perform raised-chassis single-wheel acceptance tests later |
| High before motion | What happens on communication loss or MCU reset? | Vendor manual defines timed commands and stop value, but no verified failsafe behavior | Automatic stop requirement | Never use unbounded motion in first tests | Bench-test one raised wheel with bounded command and communication interruption |
| Medium | What unit does `Ttime` actually use? | Manual text says seconds while examples such as `T1000` imply a conflicting interpretation | Motion timeout calculation | Treat duration semantics as unresolved | Time a low-speed raised-wheel command |
| Medium | Can the vendor Bluetooth connector coexist cleanly with motor traffic? | It shares the USART3-related baseboard nets rather than a separate MCU UART | Host protocol parsing and collision risk | Reserve USART2 as the independent host link | Capture traffic with Bluetooth and a bus motor connected |
| Medium | Are 5 V powered sensor outputs MCU-safe? | Sensor supply is selectable 3.3/5 V; signal lines are direct to ADC-capable MCU pins | External sensor safety | Use 3.3 V sensors or explicit level shifting | Check each module output specification or measure it |
| Tooling | Which Keil compiler, STM32F1 DFP and CubeF1 package will be pinned? | Historical machine snapshot exists but has not been refreshed | Reproducible generation/build | Do not generate target project | Configure `tools/local.env.ps1`, fix doctor search paths and run doctor |

## Known vendor-project conflict

The vendor Keil target names `STM32F103C8` and its metadata mentions medium-density startup, but its active preprocessor define and included startup file use `STM32F10X_HD` / `startup_stm32f10x_hd.s`. A clean project must select the correct medium-density C8 startup and must not copy this configuration.
