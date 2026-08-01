# Phase 6 交接

## 交接基线

- 仓库：`https://github.com/chbq/c5-car-playground.git`
- 分支：`codex/phase5d-fov-control`
- 精确提交：以 U 盘 `manifests/git-state.txt` 为准；包含本文件的提交即交接基线。
- C5 是唯一活动硬件目标；`reference/c5-vendor/` 只读，C25 仅作后续参考。
- Git 只保存项目源码、测试、自动化和文档。商家资料、模型、视频及 wheel 由 U 盘
  `workspace-overlay/` 提供，不提交远端。

收到交接包后优先按根目录 `README-FIRST.md` 恢复。联网时从 GitHub 拉取指定分支并
核对提交；离线时从 `repo/c5-car-playground.bundle` 克隆。随后把
`workspace-overlay/` 内容覆盖到仓库根目录，并运行 SHA-256 校验。首条 Codex 提示词
见 `prompts/phase6-kickoff.md`。

## 已完成基线

- STM32F103C8T6 的 CubeMX + HAL + Keil AC5 工程、主机测试和安全自动化已建立。
- USART3 总线电机、麦轮三轴混控、主动停车、HOST 看门狗和 PS2/SWD 切换已实现。
- Orange Pi 5 Pro 通过 USB/CH340 接 STM32 USART1；固定 11 字节协议、显式 ARM、
  QUERY/STOP、200 ms 失联停车及端口独占已实现并完成实物链路测试。
- Phase 5A 球心转向、5B 横移和 5C 侧置相机三轴球控已通过限时下地测试。
- Phase 5D 窄视角保护已通过本机与板端 65 项测试、`compileall` 和无运动 dry-run。
- Phase 6 的坐标系、状态机、轨迹预测、安全边界及分阶段实施顺序已记录在
  [goalkeeper-behavior.md](goalkeeper-behavior.md)。

## Phase 5D 未闭环项

2026-08-01 曾在明确授权后执行一次 30 秒 `ball-fov-test --execute`。程序正常到时
STOP，最终 QUERY 为 `HOST/DISARMED/STOPPED/errors=0`；CSV 共 511 周期，控制间隔
平均 58.6 ms、P95 87.0 ms、最大 107.9 ms，无周期超过 STM32 200 ms 看门狗。
26 个预测周期均为零平移，无目标/低置信度周期也均为零速。

但测试结束后确认电池已亏电，因此本轮只证明了通信与安全收尾，不能作为边缘回中、
短时预测和重捕获的实车行为验收。Phase 5D 仍为“软件/板端验证完成，实车待验”，
原始 CSV 未纳入 Git。

## Orange Pi 最后已知状态

以下为 2026-08-01 的最后观察，交接后必须重新检查，不能当作当前在线事实：

- SSH：`orangepi@192.168.137.168`；使用接收方自己的 SSH 密钥，不交接私钥。
- Python：`/home/orangepi/miniconda3/envs/yolov8/bin/python3`。
- Phase 5D staging：
  `/home/orangepi/Desktop/c5-goalkeeper-staging-phase5d-fov-20260801`。
- 默认模型：`rknnModel/model_26.7.25_i8.rknn`，6 个推理 worker，
  `NMS_THRESH=0.2`。
- 当前测试场地没有球门框；模型代码包含 `goal` 类，但球门识别、己方/对方区分和
  球门位姿均未在正式场地验证。

## Phase 6 首个纵向目标

先实现不动车的感知与回放骨架：

1. 定义带检测框、置信度、原始帧时间和数据年龄的 `PerceptionFrame`；
2. 增加 `GoalTracker`，保留己方/对方身份为显式未决输入；
3. 同步记录球、球门、IMU、控制状态和视频时间戳；
4. 支持同一录像重复运行跟踪、投影和行为算法；
5. 建立 `DISABLED/LOCALIZING/HOLD/INTERCEPT/BLOCK/RECOVER/TARGET_LOST/FAULT`
   状态机骨架，默认 dry-run、三轴输出为零。

本阶段不自动 ARM、不烧录、不动车。正式定位前还需补齐相机内外参、球场/球门/球
尺寸、己方与对方球门区分方法及可持续修正车位和航向的视觉锚点。MPU6050 漂移
yaw 和无编码器的速度积分都不能作为绝对位姿。

## 安全与接收方本机配置

- 烧录和电机运动都必须再次获得明确授权；默认检查、测试、生成和构建不得动车。
- `tools/local.env.ps1`、SSH 私钥、GitHub 凭据、Codex 会话/认证和系统 keyring 不在包内。
- 接收方从 `tools/local.env.example.ps1` 新建自己的本机配置。
- 首次访问香橙派时追加接收方公钥；不要复用交接者私钥。
- 任何实车动作均需限时、可自动 STOP，并先确认电池电压和场地安全。
