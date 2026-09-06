#ifndef C5_MOTION_CONFIG_H
#define C5_MOTION_CONFIG_H

/*
 * Values that are expected to change during raised-chassis calibration live
 * here. Logical +/-1000 maps to a conservative M370 speed cap.
 */
#define C5_MOTION_OUTPUT_LIMIT      1000
#define C5_MOTION_MAX_HOLD_MS        1000U
#define C5_MOTION_STOP_RETRY_MS      100U
#define C5_MOTOR_UART_TIMEOUT_MS     20U
#define C5_MOTOR_MAX_RPM_X10       3000U
#define C5_MOTOR_ACCEL_RPM_S        300U
#define C5_MOTOR_NORMAL_DECEL_RPM_S 600U
#define C5_MOTION_NORMAL_DECEL_MS    550U

/* M370 bring-up layout: LF, RF, LR, RR. Program these IDs before bus join. */
#define C5_MOTOR_ID_LEFT_FRONT       1U
#define C5_MOTOR_ID_RIGHT_FRONT      2U
#define C5_MOTOR_ID_LEFT_REAR        3U
#define C5_MOTOR_ID_RIGHT_REAR       4U

/* Initial installation polarity; verify each raised wheel before ground use. */
#define C5_MOTOR_SIGN_LEFT_FRONT     1
#define C5_MOTOR_SIGN_RIGHT_FRONT   -1
#define C5_MOTOR_SIGN_LEFT_REAR      1
#define C5_MOTOR_SIGN_RIGHT_REAR    -1

#endif
