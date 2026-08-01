# 球心像素横移

## 范围

Phase 5B 把球的水平像素误差映射为麦轮横移：

```text
摄像头 → RKNN → FootballTracker → BallStrafeController
       → BallStrafeSession → MotionLink → STM32 → 左右横移
```

本阶段固定 `vx=0、wz=0`，只输出 `vy`。首轮实测确认当前相机/底盘方向与软件
初始假设相反，因此 C5 默认使用 `lateral_sign=-1`；不使用球的纵向像素、球门、
IMU 或场地坐标。

## 初始参数

```text
error = (ball_x - image_width / 2) / (image_width / 2)
```

| 参数 | 初值 | 作用 |
|---|---:|---|
| 置信度 | 0.35 | 低于此值按无目标处理 |
| 死区 | 0.10 | 1280 宽画面中央约 ±64 像素停车 |
| `Kp` | 1000 | 归一化误差到 `vy` |
| 最小 `vy` | 250 | 越过死区后的起步目标 |
| 最大 `vy` | 800 | 协议量程 80%，为后续 `wz` 留余量 |
| 单周期变化 | 120 | 每 50 ms 最大变化量 |
| `lateral_sign` | -1 | 当前实物闭环方向；首轮 `+1` 会远离球 |

控制器限幅后再做斜率限制；换向先输出零，居中、无球和低置信度立即归零。

## 安全会话

- 20 Hz 运行，连续三周期有效目标后才 ARM；
- 默认 dry-run，只打印控制量；
- `--execute` 才发送 `vx=0, vy, wz=0`；
- 横移测试最长 30 秒；
- 执行档中丢球立即刷新零 TWIST，保持到总时限，重新连续确认三周期才恢复；
- 链路错误、Ctrl+C、到时和异常退出均尝试全局 STOP；
- STM32 200 ms HOST 看门狗继续作为下位机兜底。

## 使用

板端无运动干运行：

```bash
python3 main.py --headless --mode ball-strafe-test
```

日志确认左右目标的 `vy` 符号相反、中央为零。实物测试须再次明确授权，
首轮先架空或保持宽阔地面和人工断电手段：

```bash
python3 main.py --headless --mode ball-strafe-test --execute
```

可显式覆盖 `--min-vy`、`--max-vy`、`--lateral-kp`、
`--lateral-deadband`、`--max-vy-step` 和 `--lateral-sign`；默认值已经偏积极，
首轮不再提高。

## 验收

1. 主机测试覆盖方向、死区、置信度、限幅、斜率、换向和配置校验；
2. 会话测试覆盖 dry-run、三周期 ARM、只发送 `vy`、丢球零速和到时 STOP；
3. 香橙派板端运行测试及带球 dry-run；
4. 明确授权后验证横移朝球收敛、中央停止、丢球等待、恢复和到时停车；
5. 最终 QUERY 必须为 `HOST/DISARMED/STOPPED/errors=0`。

## 后续

横移通过后再以对方球门中心或可靠姿态产生小幅 `wz`，使球控制横移、球门控制
车头朝向。没有场地定位前保持 `vx=0`，不根据球的纵向像素追球离开守门区。

## 实物结果

- 首轮 30 秒下地测试使用 `lateral_sign=+1`，车辆远离球，判定闭环符号相反；
- 默认改为 `lateral_sign=-1` 后，本机和板端 39 项测试通过；
- 修正版 30 秒下地复验中，实际发送约 `vy=-720..+528`，车辆朝球横移；
- 中央、丢球和低置信度均发送零速，到时正常 STOP；
- 最终 QUERY 为 `HOST/DISARMED/STOPPED/errors=0`；
- 用户确认横移靠近球符合预期，车头不转；本阶段固定 `wz=0`，该行为正确。
