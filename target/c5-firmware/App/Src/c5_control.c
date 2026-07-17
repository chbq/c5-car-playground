#include "c5_control.h"

#include "c5_control_config.h"

/** @brief Compare a 32-bit deadline with signed subtraction across tick wrap. */
static int C5_TimeReached(uint32_t now_ms, uint32_t deadline_ms)
{
    return ((int32_t)(now_ms - deadline_ms) >= 0) ? 1 : 0;
}

/**
 * @brief  Debounce KEY1 and stop on its raw press edge while in PS2 mode.
 * @note Long-press timing starts when the pressed state becomes stable.
 */
static void C5_Control_UpdateKey(C5_Control *control,
                                 uint8_t pressed,
                                 uint32_t now_ms)
{
    if (pressed != control->raw_key_pressed)
    {
        control->raw_key_pressed = pressed;
        control->key_change_ms = now_ms;
        if (pressed && (control->state == C5_CONTROL_PS2))
        {
            (void)C5_Remote_ForceStop(&control->remote, now_ms);
        }
    }
    if ((pressed != control->stable_key_pressed) &&
        C5_TimeReached(now_ms,
                       control->key_change_ms + C5_CONTROL_KEY_DEBOUNCE_MS))
    {
        control->stable_key_pressed = pressed;
        control->long_press_handled = 0U;
        if (pressed)
        {
            control->key_press_ms = now_ms;
        }
    }
}

void C5_Control_Init(C5_Control *control,
                     C5_Motion *motion,
                     C5_ControlReadFrame read_frame,
                     void *read_context,
                     C5_ControlModeChange enter_ps2,
                     void *enter_context,
                     C5_ControlModeChange exit_ps2,
                     void *exit_context,
                     int key_pressed,
                     uint32_t now_ms)
{
    uint8_t pressed;

    if (control == NULL)
    {
        return;
    }
    pressed = key_pressed ? 1U : 0U;
    C5_Remote_Init(&control->remote, motion, now_ms);
    control->read_frame = read_frame;
    control->read_context = read_context;
    control->enter_ps2 = enter_ps2;
    control->enter_context = enter_context;
    control->exit_ps2 = exit_ps2;
    control->exit_context = exit_context;
    control->state = C5_CONTROL_DEBUG;
    control->key_change_ms = now_ms;
    control->key_press_ms = now_ms;
    control->next_poll_ms = now_ms;
    control->raw_key_pressed = pressed;
    control->stable_key_pressed = pressed;
    control->long_press_handled = 0U;
}

void C5_Control_Service(C5_Control *control,
                        int key_pressed,
                        uint32_t now_ms)
{
    uint8_t frame[C5_PS2_FRAME_SIZE];

    if (control == NULL)
    {
        return;
    }
    C5_Control_UpdateKey(control, key_pressed ? 1U : 0U, now_ms);

    if (control->stable_key_pressed && !control->long_press_handled &&
        C5_TimeReached(now_ms,
                       control->key_press_ms + C5_CONTROL_KEY_LONG_PRESS_MS))
    {
        control->long_press_handled = 1U;
        (void)C5_Remote_ForceStop(&control->remote, now_ms);
        if (control->state == C5_CONTROL_DEBUG)
        {
            if ((control->enter_ps2 != NULL) &&
                (control->enter_ps2(control->enter_context) == 0))
            {
                C5_Remote_Init(&control->remote,
                               control->remote.motion,
                               now_ms);
                control->state = C5_CONTROL_PS2;
                control->next_poll_ms = now_ms;
            }
        }
        else
        {
            if (control->exit_ps2 != NULL)
            {
                (void)control->exit_ps2(control->exit_context);
            }
            control->state = C5_CONTROL_DEBUG;
        }
    }

    if (control->state != C5_CONTROL_PS2)
    {
        return;
    }

    C5_Remote_Service(&control->remote, now_ms);
    if (!control->stable_key_pressed &&
        C5_TimeReached(now_ms, control->next_poll_ms))
    {
        control->next_poll_ms = now_ms + C5_CONTROL_PS2_POLL_MS;
        if ((control->read_frame == NULL) ||
            (control->read_frame(control->read_context, frame) != 0))
        {
            (void)C5_Remote_ForceStop(&control->remote, now_ms);
        }
        else
        {
            (void)C5_Remote_ProcessFrame(&control->remote,
                                         frame, sizeof(frame), now_ms);
        }
    }
}

C5_ControlState C5_Control_GetState(const C5_Control *control)
{
    return (control == NULL) ? C5_CONTROL_DEBUG : control->state;
}

C5_RemoteState C5_Control_GetRemoteState(const C5_Control *control)
{
    return (control == NULL) ? C5_REMOTE_DISARMED :
                              C5_Remote_GetState(&control->remote);
}
