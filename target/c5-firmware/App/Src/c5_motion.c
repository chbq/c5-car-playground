#include "c5_motion.h"

#include "c5_mecanum.h"
#include "c5_motion_config.h"

/** @brief Compare a 32-bit deadline with signed subtraction across tick wrap. */
static int C5_TimeReached(uint32_t now_ms, uint32_t deadline_ms)
{
    return ((int32_t)(now_ms - deadline_ms) >= 0) ? 1 : 0;
}

static int16_t C5_LimitSpeed(int16_t speed)
{
    if (speed > C5_MOTION_OUTPUT_LIMIT)
    {
        return C5_MOTION_OUTPUT_LIMIT;
    }
    if (speed < -C5_MOTION_OUTPUT_LIMIT)
    {
        return -C5_MOTION_OUTPUT_LIMIT;
    }
    return speed;
}

static int16_t C5_SpeedMagnitude(int16_t speed)
{
    int32_t magnitude;

    magnitude = speed;
    if (magnitude < 0)
    {
        magnitude = -magnitude;
    }
    if (magnitude > C5_MOTION_OUTPUT_LIMIT)
    {
        magnitude = C5_MOTION_OUTPUT_LIMIT;
    }
    return (int16_t)magnitude;
}

/** @brief Encode and transmit a broadcast stop, recording its confirmation. */
static int C5_SendStop(C5_Motion *motion)
{
    char frame[C5_MOTOR_SINGLE_FRAME_SIZE + 1U];
    size_t length;

    length = C5_MotorProtocol_FormatStop(frame, sizeof(frame));
    if ((length == 0U) ||
        (motion->write(motion->write_context,
                       (const uint8_t *)frame,
                       length) != 0))
    {
        motion->stop_confirmed = 0U;
        return -1;
    }
    motion->stop_confirmed = 1U;
    return 0;
}

/** @brief Latch a fault, schedule a retry, and immediately attempt one stop. */
static void C5_EnterFault(C5_Motion *motion, uint32_t now_ms)
{
    motion->state = C5_MOTION_FAULT;
    motion->next_stop_retry_ms = now_ms + C5_MOTION_STOP_RETRY_MS;
    (void)C5_SendStop(motion);
}

int C5_Motion_Init(C5_Motion *motion,
                   C5_MotionWrite write,
                   void *write_context,
                   const C5_MotorLayout *layout,
                   uint32_t now_ms)
{
    if ((motion == NULL) || (write == NULL))
    {
        return -1;
    }

    motion->write = write;
    motion->write_context = write_context;
    motion->layout = (layout != NULL) ? layout : &C5_MOTOR_LAYOUT_VENDOR_DEFAULT;
    motion->state = C5_MOTION_UNINITIALIZED;
    motion->deadline_ms = now_ms;
    motion->next_stop_retry_ms = now_ms;
    motion->stop_confirmed = 0U;

    if (C5_SendStop(motion) != 0)
    {
        motion->state = C5_MOTION_FAULT;
        motion->next_stop_retry_ms = now_ms + C5_MOTION_STOP_RETRY_MS;
        return -1;
    }
    motion->state = C5_MOTION_STOPPED;
    return 0;
}

int C5_Motion_CommandWheels(C5_Motion *motion,
                            const C5_WheelSpeeds *speeds,
                            uint32_t hold_ms,
                            uint32_t now_ms)
{
    C5_WheelSpeeds limited;
    char frame[C5_MOTOR_GROUP_FRAME_SIZE + 1U];
    size_t length;
    uint32_t index;
    uint8_t any_motion;

    if ((motion == NULL) || (speeds == NULL) ||
        (motion->write == NULL) ||
        (motion->state == C5_MOTION_UNINITIALIZED) ||
        (motion->state == C5_MOTION_FAULT))
    {
        return -1;
    }
    if ((hold_ms == 0U) || (hold_ms > C5_MOTION_MAX_HOLD_MS))
    {
        C5_EnterFault(motion, now_ms);
        return -1;
    }

    any_motion = 0U;
    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        limited.value[index] = C5_LimitSpeed(speeds->value[index]);
        if (limited.value[index] != 0)
        {
            any_motion = 1U;
        }
    }
    if (any_motion == 0U)
    {
        return C5_Motion_Stop(motion, now_ms);
    }

    length = C5_MotorProtocol_FormatWheels(motion->layout,
                                            &limited,
                                            frame,
                                            sizeof(frame));
    if ((length == 0U) ||
        (motion->write(motion->write_context,
                       (const uint8_t *)frame,
                       length) != 0))
    {
        C5_EnterFault(motion, now_ms);
        return -1;
    }

    motion->state = C5_MOTION_MOVING;
    motion->stop_confirmed = 0U;
    motion->deadline_ms = now_ms + hold_ms;
    return 0;
}

int C5_Motion_CommandTwist(C5_Motion *motion,
                           int16_t vx,
                           int16_t vy,
                           int16_t wz,
                           uint32_t hold_ms,
                           uint32_t now_ms)
{
    C5_WheelSpeeds speeds;

    C5_Mecanum_Mix(vx, vy, wz, C5_MOTION_OUTPUT_LIMIT, &speeds);
    return C5_Motion_CommandWheels(motion, &speeds, hold_ms, now_ms);
}

int C5_Motion_Forward(C5_Motion *motion, int16_t speed,
                      uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, speed, 0, 0, hold_ms, now_ms);
}

int C5_Motion_Backward(C5_Motion *motion, int16_t speed,
                       uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, (int16_t)-speed, 0, 0,
                                  hold_ms, now_ms);
}

int C5_Motion_StrafeLeft(C5_Motion *motion, int16_t speed,
                         uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, 0, (int16_t)-speed, 0,
                                  hold_ms, now_ms);
}

int C5_Motion_StrafeRight(C5_Motion *motion, int16_t speed,
                          uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, 0, speed, 0, hold_ms, now_ms);
}

int C5_Motion_RotateCounterClockwise(C5_Motion *motion, int16_t speed,
                                     uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, 0, 0, (int16_t)-speed,
                                  hold_ms, now_ms);
}

int C5_Motion_RotateClockwise(C5_Motion *motion, int16_t speed,
                              uint32_t hold_ms, uint32_t now_ms)
{
    speed = C5_SpeedMagnitude(speed);
    return C5_Motion_CommandTwist(motion, 0, 0, speed, hold_ms, now_ms);
}

int C5_Motion_Stop(C5_Motion *motion, uint32_t now_ms)
{
    if ((motion == NULL) || (motion->write == NULL))
    {
        return -1;
    }
    if (C5_SendStop(motion) != 0)
    {
        motion->state = C5_MOTION_FAULT;
        motion->next_stop_retry_ms = now_ms + C5_MOTION_STOP_RETRY_MS;
        return -1;
    }
    motion->state = C5_MOTION_STOPPED;
    motion->deadline_ms = now_ms;
    return 0;
}

int C5_Motion_ClearFault(C5_Motion *motion, uint32_t now_ms)
{
    if ((motion == NULL) || (motion->state != C5_MOTION_FAULT))
    {
        return -1;
    }
    if (C5_SendStop(motion) != 0)
    {
        motion->next_stop_retry_ms = now_ms + C5_MOTION_STOP_RETRY_MS;
        return -1;
    }
    motion->state = C5_MOTION_STOPPED;
    motion->deadline_ms = now_ms;
    return 0;
}

void C5_Motion_Service(C5_Motion *motion, uint32_t now_ms)
{
    if ((motion == NULL) || (motion->write == NULL))
    {
        return;
    }
    if ((motion->state == C5_MOTION_MOVING) &&
        C5_TimeReached(now_ms, motion->deadline_ms))
    {
        (void)C5_Motion_Stop(motion, now_ms);
    }
    else if ((motion->state == C5_MOTION_FAULT) &&
             (motion->stop_confirmed == 0U) &&
             C5_TimeReached(now_ms, motion->next_stop_retry_ms))
    {
        motion->next_stop_retry_ms = now_ms + C5_MOTION_STOP_RETRY_MS;
        (void)C5_SendStop(motion);
    }
}

C5_MotionState C5_Motion_GetState(const C5_Motion *motion)
{
    return (motion != NULL) ? motion->state : C5_MOTION_UNINITIALIZED;
}
