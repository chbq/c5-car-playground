# C5 工具链基线

审计日期：2026-07-15

## 固定版本

| 组件 | 版本 | 路径/状态 |
|---|---|---|
| STM32CubeMX 运行时 | 6.18.0-RC3 | `D:\Program Files\STMicroelectronics\STM32Cube\STM32CubeMX\STM32CubeMX.exe` |
| CubeMX 工程数据库 | 6.12.1 / DB.6.0.121 | 本项目保持兼容版本 |
| STM32CubeProgrammer | 2.16.0 | D 盘安装 |
| Keil µVision | 5.38.0 | `C:\Keil_v5\UV4\UV4.exe` |
| ARM Compiler | AC5.06u7 build 960 | C5 首版编译器 |
| 备用编译器 | AC6.19 | 保留用于兼容性验证 |
| STM32CubeF1 | 1.8.7 | 从本机 1.8.5/1.8.6/1.8.7 中选定 |
| STM32F1xx DFP | 2.4.1 | 已安装，含 STM32F103C8 |
| Python | 3.11.7 | `D:\anaconda3\python.exe` |
| Git | 2.40.1.windows.1 | 已安装并初始化仓库 |
| Java | Temurin 21.0.10 | CubeMX 6.18 自带；系统另有 Java 11.0.27 |

CubeMX 注册表显示版本已过时；可执行文件和启动日志为 6.18.0-RC3，而 `.ioc` 有意保留 6.12.1 数据库。

本机升级残留的 `plugins/userauth.jar` 依赖已被 6.18 移除的 JxBrowser，导致启动失败。该文件已可逆重命名为 `userauth.jar.disabled`。

## 本机配置

路径写入忽略的 `tools/local.env.ps1`，模板为 `tools/local.env.example.ps1`：

- `C5_IOC_PATH`
- `C5_UVPROJX_PATH`
- `C5_KEIL_TARGET`
- `C5_FIRMWARE_IMAGE`
- `C5_SERIAL_PORT`：硬件连接前留空

## 自动化命令

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\doctor.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\generate.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 -Rebuild
```

新机器安装固定 DFP：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\install-keil-pack.ps1 -Install
```

安装器从 Keil 官方地址下载，缓存到忽略的 `build/toolchain-cache/`，校验 PDSC 后安装；重复运行不会重复安装。

SHA-256：

```text
807EA15DA5B172B916BBC47B2B87F1E621240AD208D38E82A417A2EF8191E9D1
```

## Doctor 结果

`doctor.ps1` 检查 D 盘路径、工具版本、AC5/AC6、CubeF1 和 DFP。最终退出码为 0，输出：

- `build/doctor-report.json`
- `build/doctor-report.md`

串口和调试器枚举仍需显式开关，不在默认审计中。
