#ifndef C5_CONTROL_CONFIG_H
#define C5_CONTROL_CONFIG_H

#define C5_CONTROL_KEY_DEBOUNCE_MS       30U
#define C5_CONTROL_KEY_LONG_PRESS_MS   2000U
#define C5_CONTROL_PS2_POLL_MS           50U

#define C5_REMOTE_FRAME_TIMEOUT_MS      150U
#define C5_REMOTE_COMMAND_HOLD_MS       150U
#define C5_REMOTE_NEUTRAL_FRAMES          3U
#define C5_REMOTE_STICK_DEADZONE           8

#define C5_HOST_AXIS_LIMIT              1000
#define C5_HOST_COMMAND_HOLD_MS          150U
#define C5_HOST_LINK_TIMEOUT_MS          200U
#define C5_HOST_UART_TX_TIMEOUT_MS        20U
#define C5_HOST_EVENT_QUEUE_SIZE           4U

/* Pending hardware measurement; see docs/unresolved.md. */
#define C5_KEY1_ACTIVE_LOW                1U

#endif
