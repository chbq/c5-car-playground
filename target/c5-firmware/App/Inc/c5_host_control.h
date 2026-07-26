#ifndef C5_HOST_CONTROL_H
#define C5_HOST_CONTROL_H

#include <stdint.h>

#include "c5_host_protocol.h"
#include "c5_motion.h"

typedef struct
{
    C5_Motion *motion;
    C5_HostLinkState state;
    uint32_t last_command_ms;
    uint8_t have_deadline;
} C5_HostControl;

/**
 * @brief  Initialize HOST policy as disarmed without transmitting.
 * @param[out] host    HOST policy object.
 * @param[in]  motion  Initialized motion object.
 * @param[in]  now_ms  Current monotonic millisecond tick.
 */
void C5_HostControl_Init(C5_HostControl *host,
                         C5_Motion *motion,
                         uint32_t now_ms);

/**
 * @brief  Process one validated ARM, TWIST, STOP or QUERY command.
 * @param[in,out] host     HOST policy object.
 * @param[in]     command  Validated command with axes in [-1000, 1000].
 * @param[in]     now_ms   Current monotonic millisecond tick.
 * @return Protocol result describing whether the command was applied.
 */
C5_HostResult C5_HostControl_Process(C5_HostControl *host,
                                     const C5_HostCommand *command,
                                     uint32_t now_ms);

/**
 * @brief  Stop immediately and return HOST policy to disarmed.
 * @param[in,out] host    HOST policy object.
 * @param[in]     now_ms  Current monotonic millisecond tick.
 * @return OK after a confirmed stop, otherwise MOTION_FAULT.
 */
C5_HostResult C5_HostControl_ForceStop(C5_HostControl *host,
                                       uint32_t now_ms);

/**
 * @brief  Stop and disarm after the HOST refresh deadline expires.
 * @param[in,out] host    HOST policy object.
 * @param[in]     now_ms  Current monotonic millisecond tick; wrap is supported.
 */
void C5_HostControl_Service(C5_HostControl *host, uint32_t now_ms);

/**
 * @brief  Read the current HOST arming state.
 * @param[in] host  HOST policy object; null is treated as disarmed.
 * @return Current C5_HostLinkState.
 */
C5_HostLinkState C5_HostControl_GetState(const C5_HostControl *host);

#endif
