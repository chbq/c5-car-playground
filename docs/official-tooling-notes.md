# C5 Toolchain Baseline

Audit date: 2026-07-15

## Pinned tools and packages

| Component | Selected version | Path/status |
|---|---|---|
| STM32CubeMX runtime | 6.18.0-RC3 | `D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe` |
| CubeMX project/database | 6.12.1 / DB.6.0.121 | Preserved for this baseline |
| STM32CubeProgrammer | 2.16.0 | D-drive installation resolved |
| Keil µVision | 5.38.0 | `C:\Keil_v5\UV4\UV4.exe` |
| ARM Compiler | AC5.06 update 7 build 960 | Selected for the first C5 baseline |
| Alternate compiler | AC6.19 | Installed and retained for later compatibility builds |
| STM32CubeF1 | 1.8.7 | Selected from installed 1.8.5/1.8.6/1.8.7 repositories |
| Keil STM32F1xx DFP | 2.4.1 | Installed; PDSC contains STM32F103C8 |
| Python | 3.11.7 | `D:\anaconda3\python.exe` |
| Git | 2.40.1.windows.1 | Installed and repository initialized |
| Java | Bundled Temurin 21.0.10 | Used by CubeMX 6.18; system Java 11.0.27 remains installed |

The CubeMX registry display version is stale. The installed executable and its
startup log report 6.18.0-RC3, while this project's `.ioc` intentionally keeps
the 6.12.1 compatibility database.

The local CubeMX update left an obsolete `plugins/userauth.jar` dated 2025-04-14.
It referenced the JxBrowser dependency removed by CubeMX 6.18 and caused startup
to fail. The file was reversibly renamed to `userauth.jar.disabled`; all other
plugin files are from the 6.18 installation.

## Local configuration

Machine paths and selections are stored in ignored `tools/local.env.ps1`. The committed template is `tools/local.env.example.ps1`.

The local file now sets the generated project's paths:

- `C5_IOC_PATH`;
- `C5_UVPROJX_PATH`;
- `C5_KEIL_TARGET`;
- `C5_FIRMWARE_IMAGE`;
- `C5_SERIAL_PORT` remains blank until hardware is connected.

## Automation commands

Run scripts with a process-local execution-policy bypass; no machine policy is changed.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\doctor.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\generate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 -Rebuild
```

Install the pinned DFP on a fresh machine:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install-keil-pack.ps1 -Install
```

The pack installer downloads from the official Keil pack endpoint, caches the archive under ignored `build/toolchain-cache/`, validates the PDSC and installs into the configured pack root. Re-running it is idempotent.

Installed pack SHA-256:

```text
807EA15DA5B172B916BBC47B2B87F1E621240AD208D38E82A417A2EF8191E9D1
```

## Doctor result

`tools/doctor.ps1` now audits D-drive paths, executable versions, both ARM compilers, CubeF1 versions and STM32F1 DFP versions. The final run exited 0 and produced:

- `build/doctor-report.json`;
- `build/doctor-report.md`.

The audit did not enumerate serial ports or probe programmer/debug hardware. Those remain opt-in switches.
