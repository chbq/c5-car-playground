#ifndef C5_HOST_TEST_MAIN_H
#define C5_HOST_TEST_MAIN_H

#include <stdint.h>

typedef enum
{
    HAL_OK = 0,
    HAL_ERROR = 1
} HAL_StatusTypeDef;

typedef struct
{
    void *Instance;
    uint32_t RxState;
} UART_HandleTypeDef;

#define HAL_UART_STATE_READY 0x20U

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *uart,
                                      uint8_t *data,
                                      uint16_t size);
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *uart,
                                    const uint8_t *data,
                                    uint16_t size,
                                    uint32_t timeout);

#endif
