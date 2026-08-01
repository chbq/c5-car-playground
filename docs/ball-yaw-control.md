# 球心像素转向

## 范围

Phase 5A 只验证“足球检测 → 像素误差 → `wz` → HOST → 底盘转向”：

```text
摄像头 → RKNN → FootballTracker → BallYawController
       → BallYawSession → MotionLink → STM32 → 原地转向
```

`vx/vy` 始终为零。不使用球门、IMU、距离、场地坐标或拦截算法。

## 控制

水平误差为：

```text
error = (ball_x - image_width / 2) / (image_width / 2)
```

| 参数 | 初值 | 作用 |
|---|---:|---|
| 置信度 | 0.50 | 低于此值按无有效目标处理 |
| 死区 | 0.08 | 1280 宽画面中央约 ±51 像素时零速 |
| `Kp` | 120 | 像素归一化误差到 `wz` |
| 最小 `wz` | 40 | 越过死区后的低速起步值 |
| 最大 `wz` | 100 | 首轮实物测试上限 |
| 单周期变化 | 20 | 50 ms 控制周期内的最大增量 |
| `yaw_sign` | +1 | 画面右侧请求俯视顺时针 |

输出限制在固件协议的 `[-1000,1000]` 内；首轮 CLI 进一步限制为
`[-100,100]`。转向换向先过零。摄像头若镜像或安装方向相反，使用
`--yaw-sign -1`，不修改底盘坐标定义。

## 安全会话

- 20 Hz 运行，连续三周期有效目标后才 ARM；
- 中央死区发送零 TWIST并保持会话；
- 当前周期无球或低置信度立即发送零 TWIST；
- 短暂丢球后重新连续确认三周期才恢复非零运动；
- 连续丢球 0.5 秒后 STOP、解除 ARM并结束，不自动重新 ARM；
- 架空调参可显式使用 `--lost-timeout 0.5..2.0`；延长期间仍持续零速；
- 测试最长 30 秒；默认 10 秒；
- 链路错误、Ctrl+C、到时和异常退出均尝试 STOP；
- 默认 IDLE、INFERENCE 和干运行均不 ARM。

## 使用

SSH 下先做无运动干运行：

```bash
python3 main.py --headless --mode ball-yaw-test --duration 10
```

输出包含 `x/conf/error/wz/armed`。确认足球在画面左右移动时 `wz` 符号和大小
正确后，架空轮组并再次明确授权，再运行：

```bash
python3 main.py --headless --mode ball-yaw-test \
  --duration 10 --max-wz 100 --execute
```

检测间歇时可在架空测试中使用：

```bash
python3 main.py --headless --mode ball-yaw-test \
  --duration 30 --max-wz 100 --min-confidence 0.35 \
  --lost-timeout 1.5 --hold-arm-until-duration --execute
```

日志分别显示控制器 `target` 和实际发送的 `sent`，连续确认期间二者可能不同。
上述显式架空选项在总时限内遇到丢球只持续发送零 TWIST，不提前 STOP或解除 ARM；
重新连续识别三周期后恢复非零运动。到时、Ctrl+C和链路/模式故障仍全局 STOP。
没有该选项时，丢球 STOP 后立即结束，生产安全默认不变。

普通推理仍可运行：

```bash
python3 main.py --headless --mode inference
```

该模式只发布检测结果，不根据足球位置动车。

## 验收

1. 主机单测覆盖中心、左右、低置信度、限幅、换向、20 Hz 和丢球停车；
2. 板端测试、`compileall` 和干运行通过；
3. 架空验证足球在左/右时车辆向对应方向原地转向；
4. 验证中央死区、遮挡 0.5 秒、Ctrl+C 和 HOST 断联均停车；
5. 落地测试需独立授权，并保留清晰场地和人工断电手段。

## 后续

完整守门需要把球/球门检测框、时间戳、相机内外参和可靠姿态统一到场地坐标，
再实现搜索、定位、拦截与守门区保持。当前像素闭环不能判断距离，也不能限制车辆
与己方球门的相对位置。

## 实物结果

- 有球干运行确认左侧负 `wz`、中央零速、右侧正 `wz`，推理约 55–58 FPS；
- 架空确认 `yaw_sign=+1` 与实物方向一致；
- 30 秒显式测试中，右侧实际发送最高 `+100`，左侧最低约 `-87`；
- 连续丢球时保持 `armed=True/sent=0`，重新连续识别三周期后恢复运动；
- 仅在 30 秒到时后 STOP并解除 ARM，最终
  `HOST/DISARMED/STOPPED/errors=0`；
- 用户确认右转、中央停止、左转和丢球后恢复均符合预期；
- 2026-08-01 重新充电后，15 秒 `ground-check` 与完整 30 秒
  `ground-demo` 下地测试通过；最终 QUERY 为
  `HOST/DISARMED/STOPPED/errors=0`。

测试暴露并修复了暂停期间未继续刷新零 TWIST、导致 STM32 200 ms 看门狗提前解除
ARM 的问题。该路径已加入主机回归测试。

## 下地预设

预设只填入重复参数，不隐含 `--execute`，也不改变默认安全行为。省略
`--execute` 可先按同一档位 dry-run；保持 ARM 的策略只在明确执行时启用。

首次下地摸底：

```bash
python3 main.py --headless --mode ball-yaw-test \
  --profile ground-check --execute
```

固定为 15 秒、`wz=60..120`、`Kp=150`、死区 0.12、置信度 0.35。

录像演示：

```bash
python3 main.py --headless --mode ball-yaw-test \
  --profile ground-demo --execute
```

固定为 30 秒、`wz=70..160`、`Kp=200`、死区 0.12、置信度 0.35。
两者丢球均立即零速，并在总时限内保持 ARM等待恢复；链路故障、Ctrl+C和到时仍
全局 STOP。先通过 `ground-check` 才进入 `ground-demo`。
