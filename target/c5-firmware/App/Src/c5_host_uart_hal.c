#include "c5_host_uart_hal.h"

#include <string.h>

#include "c5_control_config.h"

static void C5_HostUartHal_IncrementError(C5_HostUartHal *hal)
{
    if (hal->error_count != 0xFFFFU)
    {
        ++hal->error_count;
    }
}

static void C5_HostUartHal_SetFault(C5_HostUartHal *hal,
                                    C5_HostResult result)
{
    C5_HostUartHal_IncrementError(hal);
    hal->fault_result = (uint8_t)result;
    hal->fault_pending = 1U;
}

static int C5_HostUartHal_Enqueue(C5_HostUartHal *hal,
                                  const C5_HostRxEvent *event)
{
    uint8_t next;

    next = (uint8_t)((hal->head + 1U) % C5_HOST_EVENT_QUEUE_SIZE);
    if (next == hal->tail)
    {
        C5_HostUartHal_SetFault(hal, C5_HOST_RESULT_RX_OVERFLOW);
        return -1;
    }
    hal->events[hal->head] = *event;
    hal->head = next;
    return 0;
}

void C5_HostUartHal_Init(C5_HostUartHal *hal, UART_HandleTypeDef *uart)
{
    if (hal == NULL)
    {
        return;
    }
    memset(hal, 0, sizeof(*hal));
    hal->uart = uart;
    C5_HostParser_Init(&hal->parser);
}

int C5_HostUartHal_Start(C5_HostUartHal *hal)
{
    if ((hal == NULL) || (hal->uart == NULL))
    {
        return -1;
    }
    return (HAL_UART_Receive_IT(hal->uart, &hal->rx_byte, 1U) == HAL_OK) ?
           0 : -1;
}

void C5_HostUartHal_RxCompleteIsr(C5_HostUartHal *hal)
{
    uint8_t frame[C5_HOST_FRAME_SIZE];
    C5_HostRxEvent event;
    int parsed;

    if ((hal == NULL) || (hal->uart == NULL))
    {
        return;
    }
    parsed = C5_HostParser_PushByte(&hal->parser, hal->rx_byte, frame);
    if (parsed == 1)
    {
        memset(&event, 0, sizeof(event));
        event.sequence = frame[3];
        event.result = C5_HostProtocol_DecodeCommand(frame, &event.command);
        if (event.result != C5_HOST_RESULT_OK)
        {
            C5_HostUartHal_IncrementError(hal);
        }
        (void)C5_HostUartHal_Enqueue(hal, &event);
    }
    if (HAL_UART_Receive_IT(hal->uart, &hal->rx_byte, 1U) != HAL_OK)
    {
        C5_HostUartHal_SetFault(hal, C5_HOST_RESULT_UART_ERROR);
    }
}

void C5_HostUartHal_ErrorIsr(C5_HostUartHal *hal)
{
    if ((hal == NULL) || (hal->uart == NULL))
    {
        return;
    }
    C5_HostUartHal_SetFault(hal, C5_HOST_RESULT_UART_ERROR);
    if (hal->uart->RxState == HAL_UART_STATE_READY)
    {
        if (HAL_UART_Receive_IT(hal->uart, &hal->rx_byte, 1U) != HAL_OK)
        {
            C5_HostUartHal_SetFault(hal, C5_HOST_RESULT_UART_ERROR);
        }
    }
}

int C5_HostUartHal_PopEvent(C5_HostUartHal *hal, C5_HostRxEvent *event)
{
    if ((hal == NULL) || (event == NULL))
    {
        return -1;
    }
    if (hal->tail == hal->head)
    {
        return 0;
    }
    *event = hal->events[hal->tail];
    hal->tail = (uint8_t)((hal->tail + 1U) % C5_HOST_EVENT_QUEUE_SIZE);
    return 1;
}

int C5_HostUartHal_ConsumeFault(C5_HostUartHal *hal,
                               C5_HostResult *result)
{
    if ((hal == NULL) || (result == NULL))
    {
        return -1;
    }
    if (!hal->fault_pending)
    {
        return 0;
    }
    *result = (C5_HostResult)hal->fault_result;
    hal->fault_pending = 0U;
    return 1;
}

int C5_HostUartHal_SendStatus(C5_HostUartHal *hal,
                              const C5_HostStatus *status)
{
    uint8_t frame[C5_HOST_FRAME_SIZE];

    if ((hal == NULL) || (hal->uart == NULL) ||
        (C5_HostProtocol_FormatStatus(status, frame, sizeof(frame)) !=
         C5_HOST_FRAME_SIZE))
    {
        return -1;
    }
    return (HAL_UART_Transmit(hal->uart,
                              frame,
                              (uint16_t)sizeof(frame),
                              C5_HOST_UART_TX_TIMEOUT_MS) == HAL_OK) ? 0 : -1;
}

uint16_t C5_HostUartHal_GetErrorCount(const C5_HostUartHal *hal)
{
    return (hal == NULL) ? 0U : hal->error_count;
}
