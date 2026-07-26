#include "c5_host_control.h"

#include "c5_control_config.h"

static int C5_HostTimeReached(uint32_t now_ms, uint32_t deadline_ms)
{
    return ((int32_t)(now_ms - deadline_ms) >= 0) ? 1 : 0;
}

void C5_HostControl_Init(C5_HostControl *host,
                         C5_Motion *motion,
                         uint32_t now_ms)
{
    if (host == NULL)
    {
        return;
    }
    host->motion = motion;
    host->state = C5_HOST_LINK_DISARMED;
    host->last_command_ms = now_ms;
    host->have_deadline = 0U;
}

C5_HostResult C5_HostControl_ForceStop(C5_HostControl *host,
                                       uint32_t now_ms)
{
    int result;

    if ((host == NULL) || (host->motion == NULL))
    {
        return C5_HOST_RESULT_MOTION_FAULT;
    }
    result = C5_Motion_Stop(host->motion, now_ms);
    host->state = C5_HOST_LINK_DISARMED;
    host->last_command_ms = now_ms;
    host->have_deadline = 0U;
    return (result == 0) ? C5_HOST_RESULT_OK :
                           C5_HOST_RESULT_MOTION_FAULT;
}

C5_HostResult C5_HostControl_Process(C5_HostControl *host,
                                     const C5_HostCommand *command,
                                     uint32_t now_ms)
{
    int result;

    if ((host == NULL) || (host->motion == NULL) || (command == NULL))
    {
        return C5_HOST_RESULT_BAD_PAYLOAD;
    }
    if (command->type == C5_HOST_COMMAND_QUERY)
    {
        return C5_HOST_RESULT_OK;
    }
    if (command->type == C5_HOST_COMMAND_STOP)
    {
        return C5_HostControl_ForceStop(host, now_ms);
    }
    if (command->type == C5_HOST_COMMAND_ARM)
    {
        if (C5_Motion_Stop(host->motion, now_ms) != 0)
        {
            host->state = C5_HOST_LINK_DISARMED;
            host->have_deadline = 0U;
            return C5_HOST_RESULT_MOTION_FAULT;
        }
        host->state = C5_HOST_LINK_ARMED;
        host->last_command_ms = now_ms;
        host->have_deadline = 1U;
        return C5_HOST_RESULT_OK;
    }
    if (command->type != C5_HOST_COMMAND_TWIST)
    {
        return C5_HOST_RESULT_BAD_TYPE;
    }
    if (host->state != C5_HOST_LINK_ARMED)
    {
        return C5_HOST_RESULT_NOT_ARMED;
    }

    if ((command->vx == 0) && (command->vy == 0) && (command->wz == 0))
    {
        result = C5_Motion_Stop(host->motion, now_ms);
    }
    else
    {
        result = C5_Motion_CommandTwist(host->motion,
                                       command->vx,
                                       command->vy,
                                       command->wz,
                                       C5_HOST_COMMAND_HOLD_MS,
                                       now_ms);
    }
    if (result != 0)
    {
        host->state = C5_HOST_LINK_DISARMED;
        host->have_deadline = 0U;
        return C5_HOST_RESULT_MOTION_FAULT;
    }
    host->last_command_ms = now_ms;
    host->have_deadline = 1U;
    return C5_HOST_RESULT_OK;
}

void C5_HostControl_Service(C5_HostControl *host, uint32_t now_ms)
{
    if ((host == NULL) || (host->state != C5_HOST_LINK_ARMED) ||
        !host->have_deadline)
    {
        return;
    }
    if (C5_HostTimeReached(now_ms,
                           host->last_command_ms + C5_HOST_LINK_TIMEOUT_MS))
    {
        (void)C5_HostControl_ForceStop(host, now_ms);
    }
}

C5_HostLinkState C5_HostControl_GetState(const C5_HostControl *host)
{
    return (host == NULL) ? C5_HOST_LINK_DISARMED : host->state;
}
