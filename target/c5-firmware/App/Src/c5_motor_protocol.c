#include "c5_motor_protocol.h"

#include "c5_motion_config.h"

#define C5_M370_COMMAND_VELOCITY  0xF6U
#define C5_M370_COMMAND_STOP      0xFEU
#define C5_M370_STOP_KEY          0x98U
#define C5_M370_COMMAND_MULTI     0xAAU
#define C5_M370_CHECK_BYTE        0x6BU
#define C5_M370_SYNC_DISABLED     0x00U
#define C5_M370_BROADCAST_ID      0x00U
#define C5_M370_STOP_SUBFRAME_SIZE   5U

const C5_MotorLayout C5_MOTOR_LAYOUT_DEFAULT =
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

static void C5_WriteU16Be(uint8_t *output, uint16_t value)
{
    output[0] = (uint8_t)(value >> 8);
    output[1] = (uint8_t)(value & 0xFFU);
}

static int C5_LayoutIsValid(const C5_MotorLayout *layout);

static void C5_WriteVelocity(uint8_t *output,
                             uint8_t id,
                             uint8_t direction,
                             uint16_t speed_rpm_tenths,
                             uint16_t acceleration_rpm_s)
{
    output[0] = id;
    output[1] = C5_M370_COMMAND_VELOCITY;
    output[2] = direction;
    C5_WriteU16Be(&output[3], acceleration_rpm_s);
    C5_WriteU16Be(&output[5], speed_rpm_tenths);
    output[7] = C5_M370_SYNC_DISABLED;
    output[8] = C5_M370_CHECK_BYTE;
}

static size_t C5_FormatWheelsAtAcceleration(
    const C5_MotorLayout *layout,
    const C5_WheelSpeeds *speeds,
    uint16_t acceleration_rpm_s,
    uint8_t *output,
    size_t capacity)
{
    uint32_t index;
    uint32_t offset;
    int32_t directed_speed;

    if ((layout == NULL) || (speeds == NULL) || (output == NULL) ||
        (acceleration_rpm_s == 0U) ||
        (capacity < C5_MOTOR_GROUP_FRAME_SIZE) ||
        !C5_LayoutIsValid(layout))
    {
        return 0U;
    }

    output[0] = C5_M370_BROADCAST_ID;
    output[1] = C5_M370_COMMAND_MULTI;
    C5_WriteU16Be(&output[2], C5_MOTOR_GROUP_FRAME_SIZE);
    offset = 4U;

    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        directed_speed = C5_MotorProtocol_ClampSpeed(speeds->value[index]);
        directed_speed *= layout->sign[index];
        C5_WriteVelocity(&output[offset],
                         layout->id[index],
                         (directed_speed < 0) ? 1U : 0U,
                         C5_MotorProtocol_SpeedToRpmTenths(
                             (int16_t)directed_speed),
                         acceleration_rpm_s);
        offset += C5_MOTOR_VELOCITY_FRAME_SIZE;
    }

    output[offset] = C5_M370_CHECK_BYTE;
    return C5_MOTOR_GROUP_FRAME_SIZE;
}

static int C5_LayoutIsValid(const C5_MotorLayout *layout)
{
    uint32_t index;
    uint32_t other;

    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        if ((layout->id[index] == C5_M370_BROADCAST_ID) ||
            ((layout->sign[index] != 1) && (layout->sign[index] != -1)))
        {
            return 0;
        }
        for (other = index + 1U; other < C5_MOTOR_COUNT; ++other)
        {
            if (layout->id[index] == layout->id[other])
            {
                return 0;
            }
        }
    }
    return 1;
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

uint16_t C5_MotorProtocol_SpeedToRpmTenths(int16_t speed)
{
    int32_t magnitude;

    magnitude = C5_MotorProtocol_ClampSpeed(speed);
    if (magnitude < 0)
    {
        magnitude = -magnitude;
    }
    return (uint16_t)((magnitude * C5_MOTOR_MAX_RPM_X10) /
                      C5_MOTOR_SPEED_MAX);
}

size_t C5_MotorProtocol_FormatStop(const C5_MotorLayout *layout,
                                   uint8_t *output,
                                   size_t capacity)
{
    uint32_t index;
    uint32_t offset;

    if ((layout == NULL) || (output == NULL) ||
        (capacity < C5_MOTOR_STOP_FRAME_SIZE) ||
        !C5_LayoutIsValid(layout))
    {
        return 0U;
    }

    output[0] = C5_M370_BROADCAST_ID;
    output[1] = C5_M370_COMMAND_MULTI;
    C5_WriteU16Be(&output[2], C5_MOTOR_STOP_FRAME_SIZE);
    offset = 4U;
    for (index = 0U; index < C5_MOTOR_COUNT; ++index)
    {
        output[offset] = layout->id[index];
        output[offset + 1U] = C5_M370_COMMAND_STOP;
        output[offset + 2U] = C5_M370_STOP_KEY;
        output[offset + 3U] = C5_M370_SYNC_DISABLED;
        output[offset + 4U] = C5_M370_CHECK_BYTE;
        offset += C5_M370_STOP_SUBFRAME_SIZE;
    }
    output[offset] = C5_M370_CHECK_BYTE;
    return C5_MOTOR_STOP_FRAME_SIZE;
}

size_t C5_MotorProtocol_FormatWheels(const C5_MotorLayout *layout,
                                     const C5_WheelSpeeds *speeds,
                                     uint8_t *output,
                                     size_t capacity)
{
    return C5_FormatWheelsAtAcceleration(layout,
                                         speeds,
                                         C5_MOTOR_ACCEL_RPM_S,
                                         output,
                                         capacity);
}

size_t C5_MotorProtocol_FormatControlledStop(
    const C5_MotorLayout *layout,
    uint16_t decel_rpm_s,
    uint8_t *output,
    size_t capacity)
{
    const C5_WheelSpeeds zero_speeds = {{0, 0, 0, 0}};

    return C5_FormatWheelsAtAcceleration(layout,
                                         &zero_speeds,
                                         decel_rpm_s,
                                         output,
                                         capacity);
}
