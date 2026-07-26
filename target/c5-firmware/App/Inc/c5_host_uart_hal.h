#ifndef C5_HOST_UART_HAL_H
#define C5_HOST_UART_HAL_H

#include <stdint.h>

#include "c5_control_config.h"
#include "c5_host_protocol.h"
#include "main.h"

typedef struct
{
    C5_HostCommand command;
    C5_HostResult result;
    uint8_t sequence;
} C5_HostRxEvent;

typedef struct
{
    UART_HandleTypeDef *uart;
    C5_HostParser parser;
    C5_HostRxEvent events[C5_HOST_EVENT_QUEUE_SIZE];
    uint8_t rx_byte;
    volatile uint8_t head;
    volatile uint8_t tail;
    volatile uint8_t fault_pending;
    volatile uint8_t fault_result;
    volatile uint16_t error_count;
} C5_HostUartHal;

/**
 * @brief  Bind the selected HOST UART and clear parser, queue and error state.
 * @param[out] hal   HOST UART adapter.
 * @param[in]  uart  Initialized UART handle.
 */
void C5_HostUartHal_Init(C5_HostUartHal *hal, UART_HandleTypeDef *uart);

/**
 * @brief  Start one-byte interrupt reception.
 * @param[in,out] hal  HOST UART adapter.
 * @retval 0   Reception armed.
 * @retval -1  Invalid input or HAL failure.
 */
int C5_HostUartHal_Start(C5_HostUartHal *hal);

/**
 * @brief  Feed the completed byte and re-arm reception from HAL RX callback.
 * @param[in,out] hal  HOST UART adapter.
 * @note Call only for the bound UART inside HAL_UART_RxCpltCallback().
 */
void C5_HostUartHal_RxCompleteIsr(C5_HostUartHal *hal);

/**
 * @brief  Record a UART error and restart reception when HAL is ready.
 * @param[in,out] hal  HOST UART adapter.
 * @note Call only for the bound UART inside HAL_UART_ErrorCallback().
 */
void C5_HostUartHal_ErrorIsr(C5_HostUartHal *hal);

/**
 * @brief  Pop one decoded or rejected complete-frame event in main context.
 * @param[in,out] hal    HOST UART adapter.
 * @param[out]    event  Output event.
 * @retval 1   Event returned.
 * @retval 0   Queue empty.
 * @retval -1  Invalid input.
 */
int C5_HostUartHal_PopEvent(C5_HostUartHal *hal, C5_HostRxEvent *event);

/**
 * @brief  Consume an asynchronous UART/queue fault in main context.
 * @param[in,out] hal     HOST UART adapter.
 * @param[out]    result  RX_OVERFLOW or UART_ERROR.
 * @retval 1   Fault returned and cleared.
 * @retval 0   No pending fault.
 * @retval -1  Invalid input.
 */
int C5_HostUartHal_ConsumeFault(C5_HostUartHal *hal,
                               C5_HostResult *result);

/**
 * @brief  Send one fixed status frame with blocking HAL UART transmit.
 * @param[in,out] hal     HOST UART adapter.
 * @param[in]     status  Status to encode.
 * @retval 0   Status transmitted.
 * @retval -1  Invalid input, format failure or HAL transmit failure.
 */
int C5_HostUartHal_SendStatus(C5_HostUartHal *hal,
                              const C5_HostStatus *status);

/**
 * @brief  Read the saturating protocol/UART error count.
 * @param[in] hal  HOST UART adapter; null returns zero.
 * @return Current error count.
 */
uint16_t C5_HostUartHal_GetErrorCount(const C5_HostUartHal *hal);

#endif
