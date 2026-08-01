# 验收门槛

## 门槛 0：建项准备

- [x] 已记录需求、系统结构和引脚预算
- [x] MCU 确认为 STM32F103C8T6
- [x] 商家资料中没有可复用的 `.ioc`
- [x] 采用商家源码中的 8 MHz HSE
- [x] 已记录 H1 与 SWD 映射，线缆实测推迟到接线时
- [x] 暂按商家原理图版本实施，实物不符时再修订
- [x] Git `main` 已同步至私有远端
- [x] 商家资料受仓库规则保护，未复制进固件

## 门槛 A：环境

- [x] CubeMX 运行时 6.18.0-RC3；工程保持 6.12.1 兼容数据库
- [x] Keil µVision 5.38、CubeProgrammer 2.16.0 已定位
- [x] 本机路径写入忽略的 `tools/local.env.ps1`
- [x] 固定 STM32CubeF1 1.8.7、STM32F1xx DFP 2.4.1
- [x] DFP 包含 STM32F103C8
- [x] 首版使用 AC5.06u7；保留 AC6.19
- [x] `doctor.ps1` 退出码为 0

## 门槛 B：最小工程

- [x] `.ioc` 可重新生成 MDK-ARM 工程
- [x] AC5 重建 0 error、0 warning
- [x] 固件输出路径明确
- [x] 实测复位/上电且未使能 dead-man 时所有电机均不动作
- [x] 已记录诊断串口配置
- [x] 未把编译通过等同于硬件可用

## 门槛 C：烧录与启动

- [ ] 使用显式烧录确认参数
- [x] 调试器通过核心板排针完成 SWD 连接
- [x] 当前镜像已写入并运行
- [x] 复位启动正常
- [ ] 收到启动诊断信息

## 门槛 D：电机

- [x] 架空底盘
- [ ] 实测四轮 ID 与位置
- [x] 验证四轮可驱动，前后、横移和旋转方向正确
- [x] 验证限时动作和自动停车
- [x] 验证 HOST 发送进程强制终止后的自动停车

## 门槛 E：PS2 遥控

- [x] CubeMX 可生成 PA8 KEY1 输入和上电 SWD 配置
- [x] PS2 协议、映射和模式策略通过 `/W4 /WX` 主机测试
- [x] 完整目标以 AC5 0 error、0 warning 构建
- [x] 实测 KEY1 低有效配置可完成双向长按切换
- [ ] 切换 PA13/PA14 前断开 ST-LINK
- [x] 接收器在手柄 MODE 常亮后连续返回有效模拟中位帧
- [x] KEY1 短按立即回到未解锁状态
- [ ] 验证 dead-man 松开和接收器物理断开均能停车
- [ ] 解决手柄关机后接收器仍返回合法帧的无线失联判定
- [ ] KEY1 长按退出后可重新连接 SWD
- [x] 架空验证 dead-man 与三轴方向

## 门槛 F：香橙派 HOST 链路

- [x] C/Python 共享 CRC8 黄金帧和有符号边界测试
- [x] STM32 分片、连续帧、垃圾重同步、坏帧、ARM/STOP、超时、tick 回绕、PS2 互斥和队列溢出测试
- [x] Python 打包、解析、状态、ACK 和链路超时测试
- [x] USART1 中断接收与 HOST/PS2 仲裁通过 AC5 0 error、0 warning 构建
- [x] SSH 只读检查系统、Python、RKNN 和用户串口权限组
- [x] Orange Pi 枚举 CH340，并确认稳定设备路径和读写权限
- [x] 重复打开/关闭 CH340 20 次，未使 MCU 卡在 Bootloader
- [x] 与 STM32 完成 QUERY、STOP、零速 ARM/TWIST、200 ms 自动解除 ARM 和坏 CRC 恢复
- [x] 用户已烧录本阶段固件
- [x] mask `brltty-udev`，并在重启后复验 CH340、doctor 和 QUERY
- [x] 架空低速验证 `vx`、`vy`、`wz`、两组 45°斜移和 STOP
- [x] 验证上位机进程被 `SIGKILL` 后的 200 ms 停车并解除 ARM
- [ ] 验证 HOST/PS2 互斥及退出 PS2 后必须重新 ARM
- [ ] 不在本阶段进行落地自动行驶

## 门槛 G：球心像素转向

- [x] 像素误差、死区、置信度、限幅、换向和参数校验通过主机测试
- [x] 20 Hz、连续目标确认、短暂丢球和 0.5 秒 STOP 通过主机测试
- [x] 默认 IDLE/INFERENCE 和 `ball-yaw-test` 干运行不 ARM
- [x] 完整 `verify.ps1` 通过
- [x] 香橙派板端单测、语法检查和无球无运动干运行通过
- [x] 实测 `yaw_sign=+1`：画面右侧对应俯视顺时针，左侧反向
- [x] 架空验证左右转向、中央零速、丢球零速等待、恢复控制和到时停车
- [ ] 单独补验 Ctrl+C 停车
- [x] 固定 `ground-check` 和 `ground-demo` 参数，均保留显式 `--execute`
- [x] 单独授权并通过 15 秒 `ground-check` 和 30 秒 `ground-demo` 下地测试

## 门槛 H：球心像素横移

- [x] `vy` 方向、死区、置信度、限幅、斜率、换向和配置通过主机测试
- [x] 20 Hz、三周期 ARM、只发送 `vy`、丢球零速和 STOP 通过主机测试
- [x] 默认 `ball-strafe-test` dry-run，不隐含 `--execute`
- [x] 香橙派板端 39 项测试和语法检查
- [x] 用户明确允许跳过 dry-run，直接完成修正符号后的带球复验
- [x] 使用 `lateral_sign=-1` 复验车辆朝球横移
- [x] 验证中央停车、丢球零速等待、恢复和到时 STOP
- [x] 最终 QUERY 为 `HOST/DISARMED/STOPPED/errors=0`

## 门槛 I：侧置相机球控

- [x] 相机右置及 `vx>0` 使镜头向画面左侧平移已由用户确认
- [x] 左球 `vx>0`、右球 `vx<0`、中央零速和换向过零通过主机测试
- [x] 远球 `vy>0`、近球 `vy<0`、目标距离零速通过主机测试
- [x] 三轴上位机同比限幅，绝对值之和不超过 1000
- [x] 三周期 ARM、丢球零速、恢复和 STOP 通过主机测试
- [x] 20 Hz CSV 覆盖检测、误差、目标/发送三轴、状态和 IMU
- [x] 默认 `ball-follow-test` dry-run，不隐含 `--execute`
- [x] 香橙派板端 57 项测试、语法、CLI、dry-run 和 60 行 CSV
- [x] 30 秒实测镜头随球左右、前后移动，同时车头转向球
- [x] CSV 验证无球、低置信度零速和控制间隔小于 200 ms
- [x] 到时 STOP，最终 QUERY 为 `HOST/DISARMED/STOPPED/errors=0`

## 门槛 J：窄视角保护

- [x] `ball-fov-test` 独立于已通过实车的 Phase 5C 模式
- [x] 中央/跟踪/边缘分区、进入/退出滞回和提前预测通过主机测试
- [x] 边缘区平移降权，`wz` 优先占用三轴总预算
- [x] 重复边缘周期不会重复缩放或异常衰减平移量
- [x] 短时丢球只允许已 ARM 会话发送零平移预测转向
- [x] 预测最多保持 150 ms，超龄后三轴归零且不提前结束运行会话
- [x] CSV 包含滤波误差、误差速度、预测误差、区域、目标年龄和丢帧数
- [x] 本机完整 RK 65 项测试和 `compileall` 通过
- [x] 香橙派板端 65 项测试、compileall、CLI 和 5 秒无运动 dry-run
- [x] dry-run 58 行 CSV 含新增字段，全程未 ARM，最终 QUERY 安全
- [ ] 限时实车验证边缘回中、丢球归零、重捕获和到时 STOP
