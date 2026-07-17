#include "c5_motor_protocol.h"

#include "c5_motion_config.h"

const C5_MotorLayout C5_MOTOR_LAYOUT_VENDOR_DEFAULT =
{
    {
        C5_MOTOR_ID_LEFT_FRONT,
        C5_MOTOR_ID_RIGHT_FRONT,
        C5_MOTOR_ID_LEFT_REAR,
        C5_MOTOR_ID_RIGHT_REAR
    },
    {
        C5_MOTOR_SIGN_LEFT_FRONT,
        C5_MOTOR_SIGN_RIGHT_FRONT,
        C5_MOTOR_SIGN_LEFT_REAR,
        C5_MOTOR_SIGN_RIGHT_REAR
    }
};

static void C5_Write3(char *output, uint16_t value)
{
    output[0] = (char)('0' + ((value / 100U) % 10U));
    output[1] = (char)('0' + ((value / 10U) % 10U));
    output[2] = (char)('0' + (value % 10U));
}

static void C5_Write4(char *output, uint16_t value)
{
    output[0] = (char)('0' + ((value / 1000U) % 10U));
    output[1] = (char)('0' + ((value / 100U) % 10U));
    output[2] = (char)('0' + ((value / 10U) % 10U));
    output[3] = (char)('0' + (value % 10U));
}

static void C5_WriteCommand(char *output,
                            uint8_t id,
                            uint16_t pulse,
                            uint16_t time)
{
    output[0] = '#';
    C5_Write3(&output[1], id);
    output[4] = 'P';
    C5_Write4(&output[5], pulse);
    output[9] = 'T';
    C5_Write4(&output[10], time);
    output[14] = '!';
}

int16_t C5_MotorProtocol_ClampSpeed(int32_t speed)
{
    if (speed > C5_MOTOR_SPEED_MAX)
    {
        return C5_MOTOR_SPEED_MAX;
    }
    if (speed < C5_MOTOR_SPEED_MIN)
    {
        return C5_MOTOR_SPEED_MIN;
    }
    return (int16_t)speed;
}

uint16_t C5_MotorProtocol_SpeedToPulse(int16_t speed, int8_t sign)
{
    int32_t pulse;

    speed = C5_MotorProtocol_ClampSpeed(speed);
    pulse = (int32_t)C5_MOTOR_PULSE_STOP + ((int32_t)speed * sign);
    if (pulse < C5_MOTOR_PULSE_MIN)
    {
        pulse = C5_MOTOR_PULSE_MIN;
    }
    if (pulse > C5_MOTOR_PULSE_MAX)
    {
        pulse = C5_MOTOR_PULSE_MAX;
    }
    return (uint16_t)pulse;
}

size_t C5_MotorProtocol_FormatSingleRaw(uint8_t id,
                                        uint16_t pulse,
                                        uint16_t time,
                                        char *output,
                                        size_t capacity)
{
    if ((output == NULL) ||
        (capacity < (C5_MOTOR_SINGLE_FRAME_SIZE + 1U)) ||
        (pulse < C5_MOTOR_PULSE_MIN) ||
        (pulse > C5_MOTOR_PULSE_MAX) ||
        (time > 9999U))
    {
        return 0U;
    }

    C5_WriteCommand(output, id, pulse, time);
    output[C5_MOTOR_SINGLE_FRAME_SIZE] = '\0';
    return C5_MOTOR_SINGLE_FRAME_SIZE;
}

size_t C5_MotorProtocol_FormatStop(char *output, size_t capacity)
{
    return C5_MotorProtocol_FormatSingleRaw(255U,
                                            C5_MOTOR_PULSE_STOP,
                                            0U,
                                            output,
                                            capacity);
}

size_t C5_MotorProtocol_FormatWheels(const C5_MotorLayout *layout,
                                     const C5_WheelSpeeds *speeds,
                                     char *output,
                                     size_t capacity)
{
    uint32_t index;
    uint32_t offset;
    uint16_t pulse;

    if ((layout == NULL) || (speeds == NULL) || (output == NULL) ||
        (capacity < (C5_MOTOR_GROUP_FRAME_SIZE + 1U)))
    {
        return 0U;
    }

    output[0] = '{';
    offset = 1U;
    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        if ((layout->sign[index] != 1) && (layout->sign[index] != -1))
        {
            output[0] = '\0';
            return 0U;
        }
        pulse = C5_MotorProtocol_SpeedToPulse(speeds->value[index],
                                               layout->sign[index]);
        C5_WriteCommand(&output[offset], layout->id[index], pulse, 0U);
        offset += C5_MOTOR_SINGLE_FRAME_SIZE;
    }
    output[offset++] = '}';
    output[offset] = '\0';
    return offset;
}
