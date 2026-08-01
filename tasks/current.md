# 当前任务：Phase 5D 窄视角保护

状态：本机/板端软件验证和 dry-run 完成；一次实车尝试因电池亏电无效，仍待验

## 目标

在不依赖球门和球场定位的前提下，降低窄视角相机的丢球概率。球接近画面边缘时优先
转向并降低平移；单帧/短时漏检只允许有界预测转向，随后归零等待重捕获。

## 工作项

1. [x] 新增独立 `ball-fov-test`，不改变 Phase 5C 默认控制。
2. [x] 水平误差与误差速度滤波，预测 150 ms 后画面位置。
3. [x] 中央、跟踪、边缘三区及 0.55/0.30 进入退出滞回。
4. [x] 边缘区平移降至 25%，先保留 `wz` 再分配剩余三轴预算。
5. [x] 最近可靠观测最多支持 150 ms 的零平移预测转向。
6. [x] 预测不会首次 ARM；重捕获后连续三周期才恢复三轴。
7. [x] CSV 增加滤波/预测误差、误差速度、区域、年龄和丢帧数。
8. [x] 本机完整 RK 65 项测试和 `compileall` 通过。
9. [x] 部署独立 staging，完成板端 65 项测试、CLI 和 5 秒 dry-run。
10. [ ] 充足电后经明确授权完成限时实车验收。

## 默认参数

- `error_alpha=0.55`，`rate_alpha=0.35`；
- `prediction_horizon=0.15 s`，`predict_hold=0.15 s`；
- `edge_enter=0.55`，`edge_exit=0.30`；
- 边缘区平移比例 0.25；
- `wz=60..260，Kp=320`；
- 默认 30 秒、dry-run、丢球不提前结束会话。

板端 staging 为 `c5-goalkeeper-staging-phase5d-fov-20260801`。dry-run 约 56 FPS，
写入 58 行 CSV，全程未 ARM；最终 QUERY 为
`HOST/DISARMED/STOPPED/errors=0`。

2026-08-01 的 30 秒实车尝试完成了到时 STOP 和安全 QUERY，但随后确认电池亏电，
因此不计入行为验收。该轮 CSV 的 511 个周期未违反 200 ms 看门狗，预测周期均为
零平移；仍需在电量正常时重新验证边缘回中、丢球归零和重捕获。

## 后续边界

Phase 5D 只保护相机视野，不承担球门识别、球场定位或守门决策。完整守门行为见
[`docs/goalkeeper-behavior.md`](../docs/goalkeeper-behavior.md)，后续在新任务实施。
跨用户恢复入口见 [`docs/handoff-phase6.md`](../docs/handoff-phase6.md)。
