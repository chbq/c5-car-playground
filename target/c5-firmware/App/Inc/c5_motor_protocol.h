#ifndef C5_MOTOR_PROTOCOL_H
#define C5_MOTOR_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define C5_MOTOR_COUNT                  4U
#define C5_MOTOR_SPEED_MIN           (-1000)
#define C5_MOTOR_SPEED_MAX             1000
#define C5_MOTOR_VELOCITY_FRAME_SIZE      9U
#define C5_MOTOR_STOP_FRAME_SIZE         25U
#define C5_MOTOR_GROUP_FRAME_SIZE        41U

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

extern const C5_MotorLayout C5_MOTOR_LAYOUT_DEFAULT;

/**
 * @brief  Clamp a logical wheel speed to the motion range.
 * @param[in] speed  Unitless wheel speed to clamp.
 * @return Wheel speed clamped to [-1000, 1000].
 */
int16_t C5_MotorProtocol_ClampSpeed(int32_t speed);

/**
 * @brief  Convert logical speed magnitude to M370 speed in 0.1 RPM.
 * @param[in] speed  Unitless speed; clamped internally to [-1000, 1000].
 * @return Unsigned speed scaled by C5_MOTOR_MAX_RPM_X10.
 */
uint16_t C5_MotorProtocol_SpeedToRpmTenths(int16_t speed);

/**
 * @brief  Encode one M370 AA frame containing four immediate-stop commands.
 * @param[in]  layout    Unique motor IDs and installation polarities.
 * @param[out] output    Binary output buffer.
 * @param[in]  capacity  Buffer capacity; at least 25 bytes.
 * @return 25 on success, or 0 for invalid parameters.
 * @note This function only encodes data and performs no I/O.
 */
size_t C5_MotorProtocol_FormatStop(const C5_MotorLayout *layout,
                                   uint8_t *output,
                                   size_t capacity);

/**
 * @brief  Encode one M370 AA frame containing four velocity commands.
 * @param[in]  layout    Unique motor IDs and installation polarities.
 * @param[in]  speeds    Logical LF/RF/LR/RR wheel speeds.
 * @param[out] output    Binary output buffer.
 * @param[in]  capacity  Buffer capacity; at least 41 bytes.
 * @return 41 on success, or 0 for invalid pointers, IDs, signs or capacity.
 * @note This function only encodes data and performs no I/O.
 */
size_t C5_MotorProtocol_FormatWheels(const C5_MotorLayout *layout,
                                     const C5_WheelSpeeds *speeds,
                                     uint8_t *output,
                                     size_t capacity);

/**
 * @brief  Encode four zero-speed commands with controlled deceleration.
 * @param[in]  layout       Unique motor IDs and installation polarities.
 * @param[in]  decel_rpm_s  Deceleration value in RPM/s; must be nonzero.
 * @param[out] output       Binary output buffer.
 * @param[in]  capacity     Buffer capacity; at least 41 bytes.
 * @return 41 on success, or 0 for invalid parameters.
 * @note This function only encodes data and performs no I/O.
 */
size_t C5_MotorProtocol_FormatControlledStop(
    const C5_MotorLayout *layout,
    uint16_t decel_rpm_s,
    uint8_t *output,
    size_t capacity);

#endif
