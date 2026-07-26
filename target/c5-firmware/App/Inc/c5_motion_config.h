#ifndef C5_MOTION_CONFIG_H
#define C5_MOTION_CONFIG_H

/*
 * Values that are expected to change during raised-chassis calibration live
 * here. Use the full +/-1000 range supported by the vendor motor protocol.
 */
#define C5_MOTION_OUTPUT_LIMIT      1000
#define C5_MOTION_MAX_HOLD_MS        1000U
#define C5_MOTION_STOP_RETRY_MS      100U
#define C5_MOTOR_UART_TIMEOUT_MS     20U

/* Vendor C5 wheel layout: LF, RF, LR, RR. */
#define C5_MOTOR_ID_LEFT_FRONT       6U
#define C5_MOTOR_ID_RIGHT_FRONT      7U
#define C5_MOTOR_ID_LEFT_REAR        8U
#define C5_MOTOR_ID_RIGHT_REAR       9U

/* Logical positive wheel speed is forward. Right-side hardware is inverted. */
#define C5_MOTOR_SIGN_LEFT_FRONT     1
#define C5_MOTOR_SIGN_RIGHT_FRONT   -1
#define C5_MOTOR_SIGN_LEFT_REAR      1
#define C5_MOTOR_SIGN_RIGHT_REAR    -1

#endif
