# C5 Car Codex Playground v0.2

这是一个用于 C5 四轮麦克纳姆小车的 Codex 本地开发工作台。

当前阶段的目标不是迁移 C25 工程，而是：

1. 审计 C5 商家资料和本机 STM32 工具链；
2. 创建干净的 STM32CubeMX + Keil 工程；
3. 建立可重复的生成、编译、显式烧录与验证流程；
4. 先让 C5 完成最小 bring-up；
5. 后续再逐项接入电机、编码器、麦轮运动学和业务功能。

## 目录用途

- `reference/c5-vendor/`：本机放置 C5 商家资料、原理图、例程和原始工程；默认只读且不提交 Git。
- `target/c5-firmware/`：唯一持续开发的目标工程。
- `docs/`：硬件事实、引脚表、阶段计划和验收记录；入口见 [`docs/README.md`](docs/README.md)。
- `tasks/`：Codex 当前任务与已完成任务。
- `prompts/`：分阶段启动提示词。
- `tools/`：环境检查、CubeMX 生成、Keil 构建、烧录与验收脚本。
- `tests/`：后续串口和真机测试。
- `build/`：日志和临时产物不提交；仅保留人工维护的 `task-report.md`。

## 第一次使用

1. 解压本目录。
2. 将商家原始资料完整复制到 `reference/c5-vendor/`。
3. 复制本机配置模板：

```powershell
Copy-Item .\tools\local.env.example.ps1 .\tools\local.env.ps1
```

4. 可先不填写路径，运行自动探测：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\doctor.ps1
```

5. 在目录根部启动 Codex：

```powershell
codex
```

6. 第一条消息：

```text
Read AGENTS.md, tasks/current.md, and prompts/00_first_run_audit.md.
Execute the audit task. Do not modify vendor files and do not flash hardware.
```

## 安全默认

- `doctor.ps1` 只探测，不修改工具链和硬件。
- `generate.ps1` 只有存在 `.ioc` 时才运行。
- `build.ps1` 只构建。
- `flash.ps1` 必须显式传入 `-IUnderstandThisWillFlashHardware`。
- 电机测试不包含在默认流水线中。
- 所有未知硬件事实都必须记录，禁止按“常见 STM32 小车”猜测。

## 推荐阶段

- Phase 0：资料与环境审计
- Phase 1：最小 CubeMX + Keil 工程
- Phase 2：串口启动与四轮独立低速测试
- Phase 3：编码器与单轮闭环
- Phase 4：麦轮运动学与车辆动作
- Phase 5：业务功能与 C25 参考迁移
