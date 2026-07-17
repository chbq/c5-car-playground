#include "c5_ps2.h"

#define C5_PS2_REPLY_MAGIC       0x5AU
#define C5_PS2_BUTTON_L1_MASK    0x0400U
#define C5_PS2_BUTTON_R1_MASK    0x0800U

static int C5_Abs(int value)
{
    return (value < 0) ? -value : value;
}

static int16_t C5_MapAxis(int value, int deadzone, int16_t limit)
{
    int magnitude;
    int range;

    if (C5_Abs(value) <= deadzone)
    {
        return 0;
    }

    magnitude = C5_Abs(value) - deadzone;
    range = 127 - deadzone;
    magnitude = (magnitude * (int)limit + (range / 2)) / range;
    if (magnitude > (int)limit)
    {
        magnitude = (int)limit;
    }
    return (int16_t)((value < 0) ? -magnitude : magnitude);
}

int C5_Ps2_Decode(const uint8_t *frame, size_t length, C5_Ps2State *state)
{
    if ((frame == NULL) || (state == NULL) ||
        (length != C5_PS2_FRAME_SIZE))
    {
        return -1;
    }
    if (((frame[1] != C5_PS2_MODE_ANALOG_RED) &&
         (frame[1] != C5_PS2_MODE_ANALOG_EXT)) ||
        (frame[2] != C5_PS2_REPLY_MAGIC))
    {
        return -1;
    }

    state->mode = frame[1];
    state->buttons = (uint16_t)frame[3] | ((uint16_t)frame[4] << 8);
    state->right_x = frame[5];
    state->right_y = frame[6];
    state->left_x = frame[7];
    state->left_y = frame[8];
    return 0;
}

int C5_Ps2_DeadmanPressed(const C5_Ps2State *state)
{
    uint16_t shoulders;

    if (state == NULL)
    {
        return 0;
    }
    shoulders = (uint16_t)(C5_PS2_BUTTON_L1_MASK |
                           C5_PS2_BUTTON_R1_MASK);
    return ((state->buttons & shoulders) != shoulders) ? 1 : 0;
}

int C5_Ps2_IsNeutral(const C5_Ps2State *state, int deadzone)
{
    if ((state == NULL) || (deadzone < 0) || (deadzone >= 127))
    {
        return 0;
    }
    return ((C5_Abs((int)state->right_x - 128) <= deadzone) &&
            (C5_Abs((int)state->right_y - 128) <= deadzone) &&
            (C5_Abs((int)state->left_x - 128) <= deadzone) &&
            (C5_Abs((int)state->left_y - 128) <= deadzone)) ? 1 : 0;
}

void C5_Ps2_MapTwist(const C5_Ps2State *state,
                     int deadzone,
                     int16_t limit,
                     int16_t *vx,
                     int16_t *vy,
                     int16_t *wz)
{
    if ((state == NULL) || (vx == NULL) || (vy == NULL) || (wz == NULL) ||
        (deadzone < 0) || (deadzone >= 127) || (limit <= 0))
    {
        return;
    }

    *vx = C5_MapAxis(128 - (int)state->left_y, deadzone, limit);
    *vy = C5_MapAxis((int)state->left_x - 128, deadzone, limit);
    *wz = C5_MapAxis((int)state->right_x - 128, deadzone, limit);
}
