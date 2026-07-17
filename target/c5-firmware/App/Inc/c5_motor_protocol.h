#ifndef C5_MOTOR_PROTOCOL_H
#define C5_MOTOR_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define C5_MOTOR_COUNT               4U
#define C5_MOTOR_SPEED_MIN        (-1000)
#define C5_MOTOR_SPEED_MAX          1000
#define C5_MOTOR_PULSE_STOP         1500U
#define C5_MOTOR_PULSE_MIN           500U
#define C5_MOTOR_PULSE_MAX          2500U
#define C5_MOTOR_SINGLE_FRAME_SIZE    15U
#define C5_MOTOR_GROUP_FRAME_SIZE     62U

typedef enum
{
    C5_WHEEL_LEFT_FRONT = 0,
    C5_WHEEL_RIGHT_FRONT,
    C5_WHEEL_LEFT_REAR,
    C5_WHEEL_RIGHT_REAR
} C5_Wheel;

typedef struct
{
    int16_t value[C5_MOTOR_COUNT];
} C5_WheelSpeeds;

typedef struct
{
    uint8_t id[C5_MOTOR_COUNT];
    int8_t sign[C5_MOTOR_COUNT];
} C5_MotorLayout;

extern const C5_MotorLayout C5_MOTOR_LAYOUT_VENDOR_DEFAULT;

int16_t C5_MotorProtocol_ClampSpeed(int32_t speed);
uint16_t C5_MotorProtocol_SpeedToPulse(int16_t speed, int8_t sign);

size_t C5_MotorProtocol_FormatSingleRaw(uint8_t id,
                                        uint16_t pulse,
                                        uint16_t time,
                                        char *output,
                                        size_t capacity);

size_t C5_MotorProtocol_FormatStop(char *output, size_t capacity);

size_t C5_MotorProtocol_FormatWheels(const C5_MotorLayout *layout,
                                     const C5_WheelSpeeds *speeds,
                                     char *output,
                                     size_t capacity);

#endif
