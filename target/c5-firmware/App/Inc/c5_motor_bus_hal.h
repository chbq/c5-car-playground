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

void C5_MotorBusHal_Init(C5_MotorBusHal *bus,
                         UART_HandleTypeDef *uart,
                         uint32_t timeout_ms);

int C5_MotorBusHal_Write(void *context,
                         const uint8_t *data,
                         size_t length);

#endif
