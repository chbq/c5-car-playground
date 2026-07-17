# C5 Car Codex Playground

这是一个用于 C5 四轮麦克纳姆小车的 Codex 本地开发工作台。

项目当前已完成干净的 CubeMX + Keil 基线和第一版麦轮运动软件，正在接入
PS2 手柄直控。目标是：

1. 维护可审计的 C5 硬件事实和引脚分配；
2. 用 STM32CubeMX 生成 HAL 工程，并以 Keil AC5 构建；
3. 通过 USART3 总线控制四个独立电机并实现麦轮运动学；
4. 保留 USART1 诊断、USART2 上位机链路和显式烧录流程；
5. 在运行时选择保留 SWD，或释放 PA13/PA14 给 PS2 手柄使用。

## 目录用途

- `reference/c5-vendor/`：本机放置 C5 商家资料、原理图、例程和原始工程；默认只读且不提交 Git。
- `target/c5-firmware/`：唯一持续开发的目标工程。
- `docs/`：硬件事实、引脚表、阶段计划和验收记录；入口见 [`docs/README.md`](docs/README.md)。
- `tasks/`：Codex 当前任务与已完成任务。
- `prompts/`：分阶段启动提示词。
- `tools/`：环境检查、CubeMX 生成、Keil 构建、烧录与验收脚本。
- `tests/`：主机单元测试和后续真机验收说明。
- `build/`：日志和临时产物不提交；仅保留人工维护的 `task-report.md`。

## 常用命令

```powershell
Copy-Item .\tools\local.env.example.ps1 .\tools\local.env.ps1
Set-ExecutionPolicy -Scope Process Bypass
.\tools\doctor.ps1
.\tools\test-host.ps1
.\tools\generate.ps1
.\tools\build.ps1 -Rebuild
.\tools\verify.ps1
```

## 安全默认

- `doctor.ps1` 只探测，不修改工具链和硬件。
- `generate.ps1` 以已选定的 CubeMX 6.12.1 数据库重建工程。
- `build.ps1` 只构建。
- `flash.ps1` 必须显式传入 `-IUnderstandThisWillFlashHardware`。
- 电机测试不包含在默认流水线中。
- 所有未知硬件事实都必须记录，禁止按“常见 STM32 小车”猜测。

## 当前里程碑

- Phase 0：资料与环境审计（完成）
- Phase 1：CubeMX + Keil 基线（完成）
- Phase 2：麦轮运动软件与失效停车（软件完成，待实物验收）
- Phase 3：PS2/SWD 双模式遥控（软件完成，待实物验收）
- 后续：上位机协议、实物验收和闭环功能

详细入口见 [`docs/README.md`](docs/README.md)，当前任务见
[`tasks/current.md`](tasks/current.md)。
