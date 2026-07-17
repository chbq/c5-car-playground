#ifndef C5_MECANUM_H
#define C5_MECANUM_H

#include <stdint.h>

#include "c5_motor_protocol.h"

/**
 * @brief  Mix chassis axes into four logical wheel speeds with normalization.
 * @param[in]  vx            Longitudinal axis in int16_t range; positive is
 *                           forward.
 * @param[in]  vy            Lateral axis in int16_t range; positive is right.
 * @param[in]  wz            Yaw axis in int16_t range; positive is clockwise
 *                           from above.
 * @param[in]  output_limit  Valid wheel-magnitude limit in [0, 1000].
 * @param[out] output        LF/RF/LR/RR result in
 *                           [-output_limit, output_limit]; ignored when null.
 * @note Axis sums are proportionally normalized, so inputs may span the full
 *       int16_t range without overflowing the internal int32_t mixer.
 */
void C5_Mecanum_Mix(int16_t vx,
                    int16_t vy,
                    int16_t wz,
                    int16_t output_limit,
                    C5_WheelSpeeds *output);

#endif
