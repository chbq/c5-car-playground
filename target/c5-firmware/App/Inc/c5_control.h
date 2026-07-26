#ifndef C5_CONTROL_H
#define C5_CONTROL_H

#include <stdint.h>

#include "c5_host_control.h"
#include "c5_ps2.h"
#include "c5_remote.h"

/**
 * @brief  Hardware callback that reads one PS2 frame.
 * @param[in]  context  Hardware context.
 * @param[out] frame    Fixed nine-byte output buffer.
 * @retval 0       Transfer completed; the protocol still validates content.
 * @retval nonzero Hardware read failed.
 */
typedef int (*C5_ControlReadFrame)(void *context,
                                   uint8_t frame[C5_PS2_FRAME_SIZE]);

/**
 * @brief  Hardware callback that enters or exits PS2 mode.
 * @param[in] context  Hardware context.
 * @retval 0       Mode change completed.
 * @retval nonzero Mode change failed.
 */
typedef int (*C5_ControlModeChange)(void *context);

typedef enum
{
    C5_CONTROL_DEBUG = 0,
    C5_CONTROL_PS2
} C5_ControlState;

typedef struct
{
    C5_Remote remote;
    C5_HostControl host;
    C5_ControlReadFrame read_frame;
    void *read_context;
    C5_ControlModeChange enter_ps2;
    void *enter_context;
    C5_ControlModeChange exit_ps2;
    void *exit_context;
    C5_ControlState state;
    uint32_t key_change_ms;
    uint32_t key_press_ms;
    uint32_t next_poll_ms;
    uint8_t raw_key_pressed;
    uint8_t stable_key_pressed;
    uint8_t long_press_handled;
} C5_Control;

/**
 * @brief  Initialize KEY1 debounce and the debug/PS2 mode state machine.
 * @param[out] control       Control object; starts in C5_CONTROL_DEBUG.
 * @param[in]  motion        Initialized motion object.
 * @param[in]  read_frame    PS2 frame reader.
 * @param[in]  read_context  Reader context.
 * @param[in]  enter_ps2     Callback that releases SWD and starts PS2 GPIO.
 * @param[in]  enter_context Enter callback context.
 * @param[in]  exit_ps2      Callback that releases PS2 GPIO and restores SWD.
 * @param[in]  exit_context  Exit callback context.
 * @param[in]  key_pressed   Initial KEY1 state: 0 released, nonzero pressed.
 * @param[in]  now_ms        Current millisecond tick.
 * @note Initialization neither changes hardware mode nor transmits a command.
 */
void C5_Control_Init(C5_Control *control,
                     C5_Motion *motion,
                     C5_ControlReadFrame read_frame,
                     void *read_context,
                     C5_ControlModeChange enter_ps2,
                     void *enter_context,
                     C5_ControlModeChange exit_ps2,
                     void *exit_context,
                     int key_pressed,
                     uint32_t now_ms);

/**
 * @brief  Service KEY1, long-press mode changes, PS2 polling and timeout.
 * @param[in,out] control      Control object.
 * @param[in]     key_pressed  KEY1 state: 0 released, nonzero pressed.
 * @param[in]     now_ms       Millisecond tick; 32-bit wrap is supported.
 * @note A raw KEY1 press in PS2 mode stops immediately; callbacks may block.
 */
void C5_Control_Service(C5_Control *control,
                        int key_pressed,
                        uint32_t now_ms);

/**
 * @brief  Read the current debug/PS2 mode.
 * @param[in] control  Control object; null is treated as debug mode.
 * @return Current C5_ControlState.
 */
C5_ControlState C5_Control_GetState(const C5_Control *control);

/**
 * @brief  Read the internal remote-policy state.
 * @param[in] control  Control object; null is treated as disarmed.
 * @return Current C5_RemoteState.
 */
C5_RemoteState C5_Control_GetRemoteState(const C5_Control *control);

/**
 * @brief  Apply one validated HOST command under HOST/PS2 ownership rules.
 * @param[in,out] control  Control arbiter.
 * @param[in]     command  Validated HOST command.
 * @param[in]     now_ms   Current monotonic millisecond tick.
 * @return Protocol result reported to the HOST.
 * @note STOP and QUERY are accepted in both modes; ARM and TWIST require the
 *       boot/debug HOST mode.
 */
C5_HostResult C5_Control_ProcessHostCommand(C5_Control *control,
                                            const C5_HostCommand *command,
                                            uint32_t now_ms);

/**
 * @brief  Stop all control sources after a malformed frame or UART fault.
 * @param[in,out] control  Control arbiter.
 * @param[in]     now_ms   Current monotonic millisecond tick.
 * @return OK after a confirmed stop, otherwise MOTION_FAULT.
 */
C5_HostResult C5_Control_HostFault(C5_Control *control, uint32_t now_ms);

/**
 * @brief  Fill the fixed HOST status fields from current control state.
 * @param[in]  control      Control arbiter.
 * @param[in]  sequence     Command sequence being acknowledged.
 * @param[in]  result       Command result.
 * @param[in]  error_count  Saturating UART/protocol error count.
 * @param[out] status       Filled status object.
 */
void C5_Control_GetHostStatus(const C5_Control *control,
                              uint8_t sequence,
                              C5_HostResult result,
                              uint16_t error_count,
                              C5_HostStatus *status);

/**
 * @brief  Read the HOST arming state.
 * @param[in] control  Control object; null is treated as disarmed.
 * @return Current C5_HostLinkState.
 */
C5_HostLinkState C5_Control_GetHostState(const C5_Control *control);

#endif
