#ifndef C5_MOTION_H
#define C5_MOTION_H

#include <stddef.h>
#include <stdint.h>

#include "c5_motor_protocol.h"

/**
 * @brief  Low-level frame writer used by the motion state machine.
 * @param[in] context  Caller-provided transport context.
 * @param[in] data     Complete protocol frame.
 * @param[in] length   Frame length.
 * @retval 0     Transmit succeeded.
 * @retval nonzero Transmit failed.
 */
typedef int (*C5_MotionWrite)(void *context,
                              const uint8_t *data,
                              size_t length);

typedef enum
{
    C5_MOTION_UNINITIALIZED = 0,
    C5_MOTION_STOPPED,
    C5_MOTION_MOVING,
    C5_MOTION_FAULT
} C5_MotionState;

typedef struct
{
    C5_MotionWrite write;
    void *write_context;
    const C5_MotorLayout *layout;
    C5_MotionState state;
    uint32_t deadline_ms;
    uint32_t next_stop_retry_ms;
    uint8_t stop_confirmed;
} C5_Motion;

/**
 * @brief  Initialize the motion state machine and send a broadcast stop.
 * @param[out] motion         Motion object.
 * @param[in]  write          Low-level frame writer.
 * @param[in]  write_context  Writer context.
 * @param[in]  layout         Wheel layout; null selects the vendor default.
 * @param[in]  now_ms         Current monotonic millisecond tick.
 * @retval 0   Stop confirmed; state becomes C5_MOTION_STOPPED.
 * @retval -1  Invalid input or failed stop; transmit failure latches a fault.
 */
int C5_Motion_Init(C5_Motion *motion,
                   C5_MotionWrite write,
                   void *write_context,
                   const C5_MotorLayout *layout,
                   uint32_t now_ms);

/**
 * @brief  Send independent wheel speeds with a mandatory stop deadline.
 * @param[in,out] motion   Initialized motion object.
 * @param[in]     speeds   Logical LF/RF/LR/RR int16_t speeds; each is clamped
 *                         to +/-C5_MOTION_OUTPUT_LIMIT before encoding.
 * @param[in]     hold_ms  Command lifetime in [1, 1000] milliseconds.
 * @param[in]     now_ms   Current monotonic millisecond tick.
 * @retval 0   Command sent; all-zero input is converted to a stop.
 * @retval -1  Invalid input, state, lifetime or transport; may latch a fault.
 */
int C5_Motion_CommandWheels(C5_Motion *motion,
                            const C5_WheelSpeeds *speeds,
                            uint32_t hold_ms,
                            uint32_t now_ms);

/**
 * @brief  Mix chassis axes and send a bounded four-wheel command.
 * @param[in,out] motion   Initialized motion object.
 * @param[in]     vx       int16_t axis; positive means forward.
 * @param[in]     vy       int16_t axis; positive means right.
 * @param[in]     wz       int16_t axis; positive means clockwise from above.
 * @param[in]     hold_ms  Command lifetime in [1, 1000] milliseconds.
 * @param[in]     now_ms   Current monotonic millisecond tick.
 * @retval 0   Transmit succeeded.
 * @retval -1  Invalid input, state, lifetime or transport.
 * @note The three axes accept [-32768, 32767]. Mixed wheel outputs are
 *       normalized to +/-C5_MOTION_OUTPUT_LIMIT (currently 700).
 */
int C5_Motion_CommandTwist(C5_Motion *motion,
                           int16_t vx,
                           int16_t vy,
                           int16_t wz,
                           uint32_t hold_ms,
                           uint32_t now_ms);

/**
 * @brief  Send bounded forward motion; speed is treated as a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_Forward(C5_Motion *motion, int16_t speed,
                      uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send bounded backward motion; speed is treated as a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_Backward(C5_Motion *motion, int16_t speed,
                       uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send bounded left strafe; speed is treated as a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_StrafeLeft(C5_Motion *motion, int16_t speed,
                         uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send bounded right strafe; speed is treated as a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_StrafeRight(C5_Motion *motion, int16_t speed,
                          uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send bounded counterclockwise rotation; speed is a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_RotateCounterClockwise(C5_Motion *motion, int16_t speed,
                                     uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send bounded clockwise rotation; speed is a magnitude.
 * @param[in,out] motion   Motion object.
 * @param[in]     speed    Any int16_t value; its magnitude is clamped to
 *                         [0, C5_MOTION_OUTPUT_LIMIT].
 * @param[in]     hold_ms  Lifetime in milliseconds.
 * @param[in]     now_ms   Current millisecond tick.
 * @retval 0 Success.
 * @retval -1 Failure.
 */
int C5_Motion_RotateClockwise(C5_Motion *motion, int16_t speed,
                              uint32_t hold_ms, uint32_t now_ms);

/**
 * @brief  Send an immediate broadcast stop and clear the motion deadline.
 * @param[in,out] motion  Motion object.
 * @param[in]     now_ms  Current millisecond tick.
 * @retval 0   Stop transmit succeeded.
 * @retval -1  Invalid input or failed transmit; failure latches a fault.
 */
int C5_Motion_Stop(C5_Motion *motion, uint32_t now_ms);

/**
 * @brief  Retry stop while faulted and clear the fault after confirmation.
 * @param[in,out] motion  Motion object.
 * @param[in]     now_ms  Current millisecond tick.
 * @retval 0   Stop confirmed; state becomes C5_MOTION_STOPPED.
 * @retval -1  Object is not faulted or the stop still failed.
 */
int C5_Motion_ClearFault(C5_Motion *motion, uint32_t now_ms);

/**
 * @brief  Service command expiry and fault-stop retries.
 * @param[in,out] motion  Motion object.
 * @param[in]     now_ms  Current millisecond tick; 32-bit wrap is supported.
 * @note The function waits only when it invokes a blocking writer.
 */
void C5_Motion_Service(C5_Motion *motion, uint32_t now_ms);

/**
 * @brief  Read the current motion state.
 * @param[in] motion  Motion object; null is treated as uninitialized.
 * @return Current C5_MotionState.
 */
C5_MotionState C5_Motion_GetState(const C5_Motion *motion);

#endif
