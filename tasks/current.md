# 当前任务：Phase 4 香橙派到 C5 的运动链路

状态：实现、软件验证和 CH340 架空运动验收通过；环境收尾与模式互斥待补

## 目标

打通“香橙派发送 `vx/vy/wz`，STM32 安全执行并逐帧回报状态”的完整链路；本任务不实现自动守门算法，不自动烧录或动车。

## 工作项

1. [x] 将香橙派工程整理为 `target/rk3588-goalkeeper/` 并排除模型、视频、wheel、IDE/cache 和旧 Agent 元数据。
2. [x] 默认物理链路改为 Orange Pi USB → 核心板 CH340 → C5 USART1；USART2 保留扩展。
3. [x] 实现固定 11 字节 CRC-8/ATM 命令/状态协议和 C/Python 黄金帧。
4. [x] 实现 STM32 HOST UART 中断接收、事件队列、ARM/超时和 HOST/PS2 仲裁。
5. [x] 实现 Orange Pi MotionLink、端口锁、默认 QUERY 的限幅 CLI 和只读 doctor。
6. [x] 从 `StateManager` 移除旧足球 x 坐标串口职责；`main.py` 只显示链路状态并在退出时 STOP。
7. [x] 保存并隔离本地 Keil schema 2.1 工作副本，CubeMX 生成后确定性同步 App 源码。
8. [x] 更新协议、接线、调通、验收和未决文档。
9. [x] 完成主机测试、CubeMX、AC5 和完整 `verify.ps1` 最终复验。
10. [x] 完成 SSH、USART1/CH340、烧录和架空低速三轴/斜移实测。
11. [x] SSH 确认 5 Pro/Ubuntu 22.04.5，并备份远端最新视觉源码和 7 个 RKNN 模型；哈希一致。
12. [x] 合入远端 `model_26.7.25_i8.rknn`、6 worker、NMS 0.2，同时保留新 MotionLink，未恢复 `/dev/ttyS0` 旧协议。
13. [x] 提交 `ac9322a` 并暂存部署到香橙派 `~/Desktop/c5-goalkeeper-staging-ac9322a/`；复用原模型目录，板端 10 个测试通过，未启动服务。
14. [x] 将固件 HOST 绑定迁移至 USART1；香橙派增加 CH340 自动发现、稳定端口优先和打开前 DTR/RTS 撤销。
15. [x] CH340 枚举、权限、20 次重复开关、QUERY/STOP、零速 ARM/TWIST、超时和坏 CRC 恢复通过。
16. [x] 架空三轴、两组 45°斜移和发送进程强杀后的自动停车通过。
17. [ ] 永久处理 `brltty-udev` 抢占并重启复验；HOST/PS2 互斥仍待补。

## 固定行为

- 命令：ARM、TWIST、STOP、QUERY；三轴小端 `int16_t`，范围 `[-1000,1000]`。
- 上位机 20 Hz 刷新；动作保持 150 ms，HOST 200 ms 未刷新则停车并解除 ARM。
- 上电 HOST 未解锁；ARM 成功回报后才接受非零 TWIST；零 TWIST 停车但保持 ARM。
- KEY1 长按先停车并解除 HOST，再进入 PS2；退出 PS2 后必须重新 ARM。
- PS2 拒绝 ARM/TWIST；QUERY 可用；STOP 在任何模式停车并解除控制状态。
- 坏帧、UART 错误、队列溢出、运动故障和超时均停车。

## 实物边界

CH340 稳定路径、权限、DTR/RTS 重复开关、非运动协议、架空三轴/斜移和进程强杀
停车均已通过，固件由用户烧录。`brltty-udev` 当前仅临时停止，重启会再次抢占；
须永久处理并复验。USB 物理拔线和 HOST/PS2 互斥仍待补。

下一任务才基于检测框、置信度、时间戳和 IMU 姿态实现相机投影、场地定位、球位置、拦截和守门区保持。
