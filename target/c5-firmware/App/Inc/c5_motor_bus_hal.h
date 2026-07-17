#ifndef C5_MOTOR_BUS_HAL_H
#define C5_MOTOR_BUS_HAL_H

#include <stddef.h>
#include <stdint.h>

#include "stm32f1xx_hal.h"

typedef struct
{
    UART_HandleTypeDef *uart;
    uint32_t timeout_ms;
} C5_MotorBusHal;

/**
 * @brief  Bind the motor-bus UART and blocking transmit timeout.
 * @param[out] bus         HAL adapter; ignored when null.
 * @param[in]  uart        Initialized UART handle.
 * @param[in]  timeout_ms  HAL UART transmit timeout in milliseconds.
 */
void C5_MotorBusHal_Init(C5_MotorBusHal *bus,
                         UART_HandleTypeDef *uart,
                         uint32_t timeout_ms);

/**
 * @brief  Send one motor frame through the blocking HAL UART API.
 * @param[in] context  Pointer to C5_MotorBusHal.
 * @param[in] data     Bytes to transmit.
 * @param[in] length   Byte count in the range [1, 65535].
 * @retval 0   HAL transmit succeeded.
 * @retval -1  Invalid input, timeout or HAL transmit failure.
 */
int C5_MotorBusHal_Write(void *context,
                         const uint8_t *data,
                         size_t length);

#endif
