"""
摄像头采集 Demo — 支持录像/截图/数据集采集
 s: 开始录像
 e: 停止录像并保存
 q: 退出
运行平台: Orange Pi 5 Pro (RK3588S)
"""

import cv2
import time

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 120)

actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
actual_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
fourcc_str = "".join([chr((actual_fourcc >> 8 * i) & 0xFF) for i in range(4)])
actual_fps = cap.get(cv2.CAP_PROP_FPS)
print(f"摄像头: {actual_w}x{actual_h} @ {actual_fps:.0f}fps, 格式={fourcc_str}")
print("s: 开始录像   e: 停止并保存   q: 退出")

writer = None
recording = False
record_count = 0
frames, fps_time, init_time = 0, time.time(), time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("读取帧失败")
        break

    frames += 1
    if frames % 30 == 0:
        now = time.time()
        fps = 30 / (now - fps_time)
        fps_time = now
        print(f"帧率: {fps:.1f} fps")

    if recording:
        writer.write(frame)
        elapsed = time.time() - start_time
        cv2.circle(frame, (30, 30), 12, (0, 0, 255), -1)
        cv2.putText(frame, f"REC {elapsed:.0f}s",
                    (50, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    cv2.imshow('camera', frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('s') and not recording:
        record_count += 1
        filename = f"capture_{record_count:03d}.mp4"
        writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'),
                                 30.0, (actual_w, actual_h))
        if not writer.isOpened():
            writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'avc1'),
                                     30.0, (actual_w, actual_h))
        start_time = time.time()
        recording = True
        print(f"[录像] 开始 → {filename}")

    elif key == ord('e') and recording:
        duration = time.time() - start_time
        writer.release()
        writer = None
        recording = False
        print(f"[录像] 停止 → {filename} ({duration:.1f}s)")

    elif key == ord('q'):
        break

if writer is not None:
    writer.release()
cap.release()
cv2.destroyAllWindows()
print(f"总平均帧率: {frames / (time.time() - init_time):.1f} fps")
print("退出")
