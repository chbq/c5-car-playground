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

/**
 * @brief  Clamp a logical wheel speed to the motor protocol range.
 * @param[in] speed  Unitless wheel speed to clamp.
 * @return Wheel speed clamped to [-1000, 1000].
 */
int16_t C5_MotorProtocol_ClampSpeed(int32_t speed);

/**
 * @brief  Convert a logical speed to a bus-motor pulse value.
 * @param[in] speed  Unitless speed; clamped internally to [-1000, 1000].
 * @param[in] sign   Installation polarity; layouts must use +1 or -1.
 * @return Pulse clamped to [500, 2500]; 1500 means stop.
 */
uint16_t C5_MotorProtocol_SpeedToPulse(int16_t speed, int8_t sign);

/**
 * @brief  Encode one raw bus-motor command.
 * @param[in]  id        Motor ID; 255 is the broadcast address.
 * @param[in]  pulse     Pulse in the range [500, 2500].
 * @param[in]  time      Protocol time field in the range [0, 9999].
 * @param[out] output    Output buffer, null-terminated on success.
 * @param[in]  capacity  Buffer capacity; at least 16 bytes.
 * @return 15 on success, or 0 for invalid parameters.
 */
size_t C5_MotorProtocol_FormatSingleRaw(uint8_t id,
                                        uint16_t pulse,
                                        uint16_t time,
                                        char *output,
                                        size_t capacity);

/**
 * @brief  Encode the ID 255, P1500, T0000 broadcast-stop command.
 * @param[out] output    Output buffer, null-terminated on success.
 * @param[in]  capacity  Buffer capacity; at least 16 bytes.
 * @return 15 on success, or 0 for invalid parameters.
 */
size_t C5_MotorProtocol_FormatStop(char *output, size_t capacity);

/**
 * @brief  Encode one atomic LF/RF/LR/RR four-wheel group frame.
 * @param[in]  layout    Wheel IDs and installation polarities.
 * @param[in]  speeds    Logical wheel speeds.
 * @param[out] output    Output buffer, null-terminated on success.
 * @param[in]  capacity  Buffer capacity; at least 63 bytes.
 * @return 62 on success, or 0 for invalid pointers, capacity or signs.
 */
size_t C5_MotorProtocol_FormatWheels(const C5_MotorLayout *layout,
                                     const C5_WheelSpeeds *speeds,
                                     char *output,
                                     size_t capacity);

#endif
