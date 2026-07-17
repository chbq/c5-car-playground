#ifndef C5_MOTION_H
#define C5_MOTION_H

#include <stddef.h>
#include <stdint.h>

#include "c5_motor_protocol.h"

typedef int (*C5_MotionWrite)(void *context,
                              const uint8_t *data,
                              size_t length);

typedef enum
{
    C5_MOTION_UNINITIALIZED = 0,
    C5_MOTION_STOPPED,
    C5_MOTION_MOVING,
    C5_MOTION_FAULT
} C5_MotionState;

typedef struct
{
    C5_MotionWrite write;
    void *write_context;
    const C5_MotorLayout *layout;
    C5_MotionState state;
    uint32_t deadline_ms;
    uint32_t next_stop_retry_ms;
    uint8_t stop_confirmed;
} C5_Motion;

int C5_Motion_Init(C5_Motion *motion,
                   C5_MotionWrite write,
                   void *write_context,
                   const C5_MotorLayout *layout,
                   uint32_t now_ms);

int C5_Motion_CommandWheels(C5_Motion *motion,
                            const C5_WheelSpeeds *speeds,
                            uint32_t hold_ms,
                            uint32_t now_ms);

int C5_Motion_CommandTwist(C5_Motion *motion,
                           int16_t vx,
                           int16_t vy,
                           int16_t wz,
                           uint32_t hold_ms,
                           uint32_t now_ms);

int C5_Motion_Forward(C5_Motion *motion, int16_t speed,
                      uint32_t hold_ms, uint32_t now_ms);
int C5_Motion_Backward(C5_Motion *motion, int16_t speed,
                       uint32_t hold_ms, uint32_t now_ms);
int C5_Motion_StrafeLeft(C5_Motion *motion, int16_t speed,
                         uint32_t hold_ms, uint32_t now_ms);
int C5_Motion_StrafeRight(C5_Motion *motion, int16_t speed,
                          uint32_t hold_ms, uint32_t now_ms);
int C5_Motion_RotateCounterClockwise(C5_Motion *motion, int16_t speed,
                                     uint32_t hold_ms, uint32_t now_ms);
int C5_Motion_RotateClockwise(C5_Motion *motion, int16_t speed,
                              uint32_t hold_ms, uint32_t now_ms);

int C5_Motion_Stop(C5_Motion *motion, uint32_t now_ms);
int C5_Motion_ClearFault(C5_Motion *motion, uint32_t now_ms);
void C5_Motion_Service(C5_Motion *motion, uint32_t now_ms);
C5_MotionState C5_Motion_GetState(const C5_Motion *motion);

#endif
