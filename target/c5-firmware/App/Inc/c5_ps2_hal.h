#ifndef C5_PS2_HAL_H
#define C5_PS2_HAL_H

#include <stdint.h>

#include "c5_ps2.h"

typedef struct
{
    uint32_t cycles_per_us;
    uint8_t active;
} C5_Ps2Hal;

/**
 * @brief  Clear PS2 HAL software state without changing GPIO or SWD.
 * @param[out] hal  PS2 HAL object; ignored when null.
 */
void C5_Ps2Hal_Init(C5_Ps2Hal *hal);

/**
 * @brief  Disable SWJ, configure PA12-PA15 for PS2, and start DWT timing.
 * @param[in,out] context  Pointer to C5_Ps2Hal.
 * @retval 0   Mode change succeeded.
 * @retval -1  Invalid context or timing initialization failure.
 * @warning Disconnect any probe actively driving PA13/PA14 before this call.
 */
int C5_Ps2Hal_Enter(void *context);

/**
 * @brief  Idle the PS2 bus, release PA12-PA15, and restore SWD.
 * @param[in,out] context  Pointer to C5_Ps2Hal.
 * @retval 0   Restore completed.
 * @retval -1  Invalid context.
 */
int C5_Ps2Hal_Exit(void *context);

/**
 * @brief  Read one nine-byte PS2 reply with blocking LSB-first transfers.
 * @param[in]  context  C5_Ps2Hal that has entered PS2 mode.
 * @param[out] frame    Nine-byte reply; the caller validates its content.
 * @retval 0   Transfer completed.
 * @retval -1  Invalid input or PS2 mode is inactive.
 * @note One frame occupies the CPU for about 1.5 milliseconds.
 */
int C5_Ps2Hal_ReadFrame(void *context,
                        uint8_t frame[C5_PS2_FRAME_SIZE]);

#endif
