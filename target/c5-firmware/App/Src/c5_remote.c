#include "c5_remote.h"

#include "c5_control_config.h"
#include "c5_motion_config.h"
#include "c5_ps2.h"

static int C5_TimeReached(uint32_t now_ms, uint32_t deadline_ms)
{
    return ((int32_t)(now_ms - deadline_ms) >= 0) ? 1 : 0;
}

void C5_Remote_Init(C5_Remote *remote, C5_Motion *motion, uint32_t now_ms)
{
    if (remote == NULL)
    {
        return;
    }
    remote->motion = motion;
    remote->state = C5_REMOTE_DISARMED;
    remote->last_frame_ms = now_ms;
    remote->neutral_frames = 0U;
    remote->have_valid_frame = 0U;
}

int C5_Remote_ForceStop(C5_Remote *remote, uint32_t now_ms)
{
    int result;

    if ((remote == NULL) || (remote->motion == NULL))
    {
        return -1;
    }
    result = C5_Motion_Stop(remote->motion, now_ms);
    remote->state = C5_REMOTE_DISARMED;
    remote->neutral_frames = 0U;
    remote->have_valid_frame = 0U;
    return result;
}

int C5_Remote_ProcessFrame(C5_Remote *remote,
                           const uint8_t *frame,
                           size_t length,
                           uint32_t now_ms)
{
    C5_Ps2State ps2;
    int16_t vx;
    int16_t vy;
    int16_t wz;

    if ((remote == NULL) || (remote->motion == NULL))
    {
        return -1;
    }
    if (C5_Ps2_Decode(frame, length, &ps2) != 0)
    {
        (void)C5_Remote_ForceStop(remote, now_ms);
        return -1;
    }

    remote->last_frame_ms = now_ms;
    remote->have_valid_frame = 1U;

    if (remote->state == C5_REMOTE_DISARMED)
    {
        if (C5_Ps2_IsNeutral(&ps2, C5_REMOTE_STICK_DEADZONE) &&
            !C5_Ps2_DeadmanPressed(&ps2))
        {
            if (remote->neutral_frames < C5_REMOTE_NEUTRAL_FRAMES)
            {
                ++remote->neutral_frames;
            }
            if (remote->neutral_frames >= C5_REMOTE_NEUTRAL_FRAMES)
            {
                remote->state = C5_REMOTE_READY;
            }
        }
        else
        {
            remote->neutral_frames = 0U;
        }
        return 0;
    }

    if (!C5_Ps2_DeadmanPressed(&ps2))
    {
        if (remote->state == C5_REMOTE_ACTIVE)
        {
            if (C5_Motion_Stop(remote->motion, now_ms) != 0)
            {
                return -1;
            }
        }
        remote->state = C5_REMOTE_READY;
        return 0;
    }

    C5_Ps2_MapTwist(&ps2,
                    C5_REMOTE_STICK_DEADZONE,
                    C5_MOTION_OUTPUT_LIMIT,
                    &vx, &vy, &wz);
    if ((vx == 0) && (vy == 0) && (wz == 0))
    {
        if (remote->state == C5_REMOTE_ACTIVE)
        {
            if (C5_Motion_Stop(remote->motion, now_ms) != 0)
            {
                return -1;
            }
        }
        remote->state = C5_REMOTE_READY;
        return 0;
    }

    if (C5_Motion_CommandTwist(remote->motion,
                              vx, vy, wz,
                              C5_REMOTE_COMMAND_HOLD_MS,
                              now_ms) != 0)
    {
        remote->state = C5_REMOTE_DISARMED;
        return -1;
    }
    remote->state = C5_REMOTE_ACTIVE;
    return 0;
}

void C5_Remote_Service(C5_Remote *remote, uint32_t now_ms)
{
    if ((remote == NULL) || (remote->motion == NULL) ||
        !remote->have_valid_frame)
    {
        return;
    }
    if (C5_TimeReached(now_ms,
                       remote->last_frame_ms + C5_REMOTE_FRAME_TIMEOUT_MS))
    {
        (void)C5_Remote_ForceStop(remote, now_ms);
    }
}

C5_RemoteState C5_Remote_GetState(const C5_Remote *remote)
{
    return (remote == NULL) ? C5_REMOTE_DISARMED : remote->state;
}
