# C5 STM32 固件

本目录是唯一长期维护的 STM32CubeMX + Keil HAL 工程，目标为 STM32F103C8T6：

- 8 MHz HSE、72 MHz SYSCLK；
- 上电保留 PA13/PA14 SWD，KEY1 长按后可切换 PS2；
- USART1 PA9/PA10：CH340 诊断/串口下载；
- USART2 PA2/PA3：Orange Pi HOST，115200，中断接收；
- USART3 PB10/PB11：四轮单线总线；
- PB13：低电平亮的 PS2 状态灯；
- PA8：上拉、低有效 KEY1。

上电主动广播停车，不自动运动。HOST 必须先 ARM 才接受非零 TWIST；150 ms 动作保持，200 ms 未刷新即停车并解除 ARM。PS2 与 HOST 互斥，STOP 始终有效。HOST 接收 ISR 只解析并投递事件，所有运动和串口发送均在主循环执行。

`App/` 保存手写逻辑；生成代码只在 `USER CODE` 区接入。CubeMX 生成后，`sync-keil-project.ps1` 会确定性加入 `App/Src/*.c` 和 `App/Inc`。

从仓库根目录验证：

```powershell
.\tools\test-host.ps1
.\tools\generate.ps1
.\tools\build.ps1 -Rebuild
.\tools\verify.ps1
```

这些命令不会烧录或驱动电机。协议和实物验收见 [`docs/host-link.md`](../../docs/host-link.md)。
