# 主机测试

`c5_motion_tests.c` 用本机 MSVC `/W4 /WX` 编译生产 C 源码，覆盖：

- 电机协议、麦轮混控、限时停车、故障重试和 tick 回绕；
- PS2 解码、dead-man、中位解锁、超时和 KEY1 模式切换；
- HOST CRC8 黄金帧、分片/连续帧、垃圾重同步、坏帧和载荷范围；
- ARM、TWIST、STOP、200 ms 超时、PS2 互斥；
- HOST UART HAL 事件队列溢出、UART 错误恢复和状态发送。

```powershell
.\tools\test-host.ps1
.\tools\test-rk-host.ps1
```

Python 测试覆盖同一协议、状态回报、ARM 门控、ACK 和状态超时。两套测试均不访问串口或驱动电机。
