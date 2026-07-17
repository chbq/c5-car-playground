#ifndef C5_PS2_HAL_H
#define C5_PS2_HAL_H

#include <stdint.h>

#include "c5_ps2.h"

typedef struct
{
    uint32_t cycles_per_us;
    uint8_t active;
} C5_Ps2Hal;

void C5_Ps2Hal_Init(C5_Ps2Hal *hal);
int C5_Ps2Hal_Enter(void *context);
int C5_Ps2Hal_Exit(void *context);
int C5_Ps2Hal_ReadFrame(void *context,
                        uint8_t frame[C5_PS2_FRAME_SIZE]);

#endif
