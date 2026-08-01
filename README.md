# C5 麦克纳姆守门员

基于 STM32CubeMX、HAL、Keil AC5 和 RK3588 的 C5 固件与自动化工作流。当前已完成：

1. 可审计的硬件事实与引脚分配；
2. 可重复生成、测试、构建和显式烧录的工具链；
3. USART3 四轮总线电机协议、麦轮混控和失效停车；
4. USART1 经 CH340 承载 USB HOST 运动协议和串口下载，USART2 保留扩展；
5. SWD/PS2 运行时切换和 dead-man 遥控；
6. 香橙派 MotionLink、串口 CLI、环境检查和视觉主程序安全接入；
7. 已通过下地测试的球心像素转向闭环；
8. 可单测、显式使能的球心像素麦轮横移闭环；
9. 面向右侧相机的 `vx` 左右、`vy` 前后、`wz` 转向三轴球控与 CSV。
10. 窄视角边缘转向优先、预测和滞回控制（软件验证完成）。

## 目录用途

- `reference/c5-vendor/`：本机放置 C5 商家资料、原理图、例程和原始工程；默认只读且不提交 Git。
- `target/c5-firmware/`：唯一持续开发的目标工程。
- `target/rk3588-goalkeeper/`：香橙派视觉与 HOST 运动链路源码；模型和视频不提交。
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
.\tools\test-rk-host.ps1
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

- 阶段 0：资料与环境审计（完成）
- 阶段 1：CubeMX + Keil 基线（完成）
- 阶段 2：麦轮运动与失效停车（架空及整车三轴运动通过，断联停车待补）
- 阶段 3：PS2/SWD 双模式遥控（PS2、KEY1 和车辆方向实测通过，SWD 恢复待补）
- 阶段 4：香橙派到 C5 的 HOST 运动链路（CH340 通信、架空三轴/斜移和断联停车通过；环境收尾待补）
- 阶段 5A：球心像素转向（15 秒与 30 秒下地测试通过）
- 阶段 5B：球心像素横移（修正方向后，30 秒下地闭环通过）
- 阶段 5C：侧置相机球控（三轴、CSV 和 30 秒实车通过）
- 阶段 5D：窄视角视野保护（本机/板端 65 项测试和 dry-run 通过，实车待验）
- 阶段 6：相机/场地定位、自动拦截和守门区保持（已设计，待新任务实施）

详细入口见 [`docs/README.md`](docs/README.md)，当前任务见
[`tasks/current.md`](tasks/current.md)。
