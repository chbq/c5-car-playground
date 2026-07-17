#include "c5_mecanum.h"

static int32_t C5_Abs32(int32_t value)
{
    return (value < 0) ? -value : value;
}

void C5_Mecanum_Mix(int16_t vx,
                    int16_t vy,
                    int16_t wz,
                    int16_t output_limit,
                    C5_WheelSpeeds *output)
{
    int32_t raw[C5_MOTOR_COUNT];
    int32_t peak;
    int32_t magnitude;
    uint32_t index;

    if (output == NULL)
    {
        return;
    }
    if (output_limit < 0)
    {
        output_limit = (int16_t)-output_limit;
    }
    if (output_limit > C5_MOTOR_SPEED_MAX)
    {
        output_limit = C5_MOTOR_SPEED_MAX;
    }

    raw[C5_WHEEL_LEFT_FRONT] = (int32_t)vx + vy + wz;
    raw[C5_WHEEL_RIGHT_FRONT] = (int32_t)vx - vy - wz;
    raw[C5_WHEEL_LEFT_REAR] = (int32_t)vx - vy + wz;
    raw[C5_WHEEL_RIGHT_REAR] = (int32_t)vx + vy - wz;

    peak = 0;
    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        magnitude = C5_Abs32(raw[index]);
        if (magnitude > peak)
        {
            peak = magnitude;
        }
    }

    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        if ((peak > output_limit) && (peak > 0))
        {
            output->value[index] = (int16_t)((raw[index] * output_limit) / peak);
        }
        else
        {
            output->value[index] = (int16_t)raw[index];
        }
    }
}
