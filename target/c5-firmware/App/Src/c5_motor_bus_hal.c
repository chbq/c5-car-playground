#include "c5_motor_bus_hal.h"

void C5_MotorBusHal_Init(C5_MotorBusHal *bus,
                         UART_HandleTypeDef *uart,
                         uint32_t timeout_ms)
{
    if (bus != NULL)
    {
        bus->uart = uart;
        bus->timeout_ms = timeout_ms;
    }
}

int C5_MotorBusHal_Write(void *context,
                         const uint8_t *data,
                         size_t length)
{
    C5_MotorBusHal *bus;

    bus = (C5_MotorBusHal *)context;
    if ((bus == NULL) || (bus->uart == NULL) || (data == NULL) ||
        (length == 0U) || (length > 65535U))
    {
        return -1;
    }

    return (HAL_UART_Transmit(bus->uart,
                              (uint8_t *)data,
                              (uint16_t)length,
                              bus->timeout_ms) == HAL_OK) ? 0 : -1;
}
