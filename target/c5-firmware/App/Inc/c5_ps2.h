#ifndef C5_PS2_H
#define C5_PS2_H

#include <stddef.h>
#include <stdint.h>

#define C5_PS2_FRAME_SIZE       9U
#define C5_PS2_MODE_ANALOG_RED  0x73U
#define C5_PS2_MODE_ANALOG_EXT  0x79U

typedef struct
{
    uint8_t mode;       /**< Analog mode ID: 0x73 or 0x79. */
    uint16_t buttons;   /**< Active-low PS2 button bitmap. */
    uint8_t right_x;    /**< Raw [0, 255], nominal center 128. */
    uint8_t right_y;    /**< Raw [0, 255], nominal center 128. */
    uint8_t left_x;     /**< Raw [0, 255], nominal center 128. */
    uint8_t left_y;     /**< Raw [0, 255], nominal center 128. */
} C5_Ps2State;

/**
 * @brief  Decode one nine-byte PS2 analog-mode response.
 * @param[in]  frame   Raw response frame.
 * @param[in]  length  Must equal C5_PS2_FRAME_SIZE.
 * @param[out] state   Decoded buttons and four axes.
 * @retval 0   Mode is 0x73/0x79 and the reply marker is 0x5A.
 * @retval -1  Invalid input, length, mode or marker.
 */
int C5_Ps2_Decode(const uint8_t *frame, size_t length, C5_Ps2State *state);

/**
 * @brief  Check whether the L1 or R1 dead-man button is pressed.
 * @param[in] state  Decoded PS2 state.
 * @return 1 when either shoulder is pressed; otherwise 0. Null returns 0.
 */
int C5_Ps2_DeadmanPressed(const C5_Ps2State *state);

/**
 * @brief  Check whether all four stick axes are inside the center deadzone.
 * @param[in] state     Decoded PS2 state.
 * @param[in] deadzone  Center deadzone in the range [0, 126].
 * @return 1 when all axes are neutral; otherwise 0.
 */
int C5_Ps2_IsNeutral(const C5_Ps2State *state, int deadzone);

/**
 * @brief  Map PS2 sticks to longitudinal, lateral and yaw axes.
 * @param[in]  state     Decoded PS2 state.
 * @param[in]  deadzone  Center deadzone in the range [0, 126].
 * @param[in]  limit     Positive output limit in [1, 32767].
 * @param[out] vx        Left-stick Y in [-limit, limit]; positive is forward.
 * @param[out] vy        Left-stick X in [-limit, limit]; positive is right.
 * @param[out] wz        Right-stick X in [-limit, limit]; positive is
 *                       clockwise from above.
 * @note Invalid parameters leave all outputs unchanged.
 */
void C5_Ps2_MapTwist(const C5_Ps2State *state,
                     int deadzone,
                     int16_t limit,
                     int16_t *vx,
                     int16_t *vy,
                     int16_t *wz);

#endif
