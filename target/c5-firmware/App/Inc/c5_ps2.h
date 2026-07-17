#ifndef C5_PS2_H
#define C5_PS2_H

#include <stddef.h>
#include <stdint.h>

#define C5_PS2_FRAME_SIZE       9U
#define C5_PS2_MODE_ANALOG_RED  0x73U
#define C5_PS2_MODE_ANALOG_EXT  0x79U

typedef struct
{
    uint8_t mode;
    uint16_t buttons;
    uint8_t right_x;
    uint8_t right_y;
    uint8_t left_x;
    uint8_t left_y;
} C5_Ps2State;

int C5_Ps2_Decode(const uint8_t *frame, size_t length, C5_Ps2State *state);
int C5_Ps2_DeadmanPressed(const C5_Ps2State *state);
int C5_Ps2_IsNeutral(const C5_Ps2State *state, int deadzone);
void C5_Ps2_MapTwist(const C5_Ps2State *state,
                     int deadzone,
                     int16_t limit,
                     int16_t *vx,
                     int16_t *vy,
                     int16_t *wz);

#endif
