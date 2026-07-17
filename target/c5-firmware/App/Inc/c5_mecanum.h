#ifndef C5_MECANUM_H
#define C5_MECANUM_H

#include <stdint.h>

#include "c5_motor_protocol.h"

/*
 * Coordinate convention:
 *   vx > 0: forward
 *   vy > 0: strafe right
 *   wz > 0: rotate clockwise when viewed from above
 */
void C5_Mecanum_Mix(int16_t vx,
                    int16_t vy,
                    int16_t wz,
                    int16_t output_limit,
                    C5_WheelSpeeds *output);

#endif
