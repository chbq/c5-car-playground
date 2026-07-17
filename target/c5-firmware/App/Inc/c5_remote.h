#ifndef C5_REMOTE_H
#define C5_REMOTE_H

#include <stddef.h>
#include <stdint.h>

#include "c5_motion.h"

typedef enum
{
    C5_REMOTE_DISARMED = 0,
    C5_REMOTE_READY,
    C5_REMOTE_ACTIVE
} C5_RemoteState;

typedef struct
{
    C5_Motion *motion;
    C5_RemoteState state;
    uint32_t last_frame_ms;
    uint8_t neutral_frames;
    uint8_t have_valid_frame;
} C5_Remote;

/**
 * @brief  Initialize the remote policy as disarmed without transmitting.
 * @param[out] remote  Remote-policy object.
 * @param[in]  motion  Initialized motion object.
 * @param[in]  now_ms  Current millisecond tick.
 */
void C5_Remote_Init(C5_Remote *remote, C5_Motion *motion, uint32_t now_ms);

/**
 * @brief  Process one PS2 frame through arming, dead-man and axis mapping.
 * @param[in,out] remote  Remote-policy object.
 * @param[in]     frame   Raw PS2 frame.
 * @param[in]     length  Frame length; must equal C5_PS2_FRAME_SIZE (9).
 * @param[in]     now_ms  Current millisecond tick.
 * @retval 0   Valid frame processed; this does not imply motion was sent.
 * @retval -1  Invalid frame/input or motion failure; invalid frames stop.
 */
int C5_Remote_ProcessFrame(C5_Remote *remote,
                           const uint8_t *frame,
                           size_t length,
                           uint32_t now_ms);

/**
 * @brief  Request an immediate stop and return the remote to disarmed.
 * @param[in,out] remote  Remote-policy object.
 * @param[in]     now_ms  Current millisecond tick.
 * @retval 0   Stop transmit succeeded.
 * @retval -1  Invalid input or failed stop transmit.
 */
int C5_Remote_ForceStop(C5_Remote *remote, uint32_t now_ms);

/**
 * @brief  Stop and disarm when the PS2 frame deadline expires.
 * @param[in,out] remote  Remote-policy object.
 * @param[in]     now_ms  Current millisecond tick; 32-bit wrap is supported.
 */
void C5_Remote_Service(C5_Remote *remote, uint32_t now_ms);

/**
 * @brief  Read the current remote-policy state.
 * @param[in] remote  Remote object; null is treated as disarmed.
 * @return Current C5_RemoteState.
 */
C5_RemoteState C5_Remote_GetState(const C5_Remote *remote);

#endif
