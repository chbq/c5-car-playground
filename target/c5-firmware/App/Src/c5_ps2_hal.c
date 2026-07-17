#include "c5_ps2_hal.h"

#include "stm32f1xx_hal.h"

#define C5_PS2_GPIO_PORT       GPIOA
#define C5_PS2_CLK_PIN         GPIO_PIN_12
#define C5_PS2_ATT_PIN         GPIO_PIN_13
#define C5_PS2_CMD_PIN         GPIO_PIN_14
#define C5_PS2_DAT_PIN         GPIO_PIN_15
#define C5_PS2_OUTPUT_PINS     (C5_PS2_CLK_PIN | C5_PS2_ATT_PIN | \
                                C5_PS2_CMD_PIN)
#define C5_PS2_ALL_PINS        (C5_PS2_OUTPUT_PINS | C5_PS2_DAT_PIN)
#define C5_PS2_EDGE_DELAY_US   10U
#define C5_PS2_SELECT_DELAY_US 10U

static void C5_Ps2Hal_DelayUs(const C5_Ps2Hal *hal, uint32_t delay_us)
{
    uint32_t start;
    uint32_t cycles;

    start = DWT->CYCCNT;
    cycles = delay_us * hal->cycles_per_us;
    while ((uint32_t)(DWT->CYCCNT - start) < cycles)
    {
    }
}

static uint8_t C5_Ps2Hal_Transfer(C5_Ps2Hal *hal, uint8_t value)
{
    uint8_t received;
    uint8_t bit;

    received = 0U;
    for (bit = 0U; bit < 8U; ++bit)
    {
        HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CMD_PIN,
                          ((value & (1U << bit)) != 0U) ?
                              GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CLK_PIN, GPIO_PIN_RESET);
        C5_Ps2Hal_DelayUs(hal, C5_PS2_EDGE_DELAY_US);
        HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CLK_PIN, GPIO_PIN_SET);
        if (HAL_GPIO_ReadPin(C5_PS2_GPIO_PORT, C5_PS2_DAT_PIN) == GPIO_PIN_SET)
        {
            received = (uint8_t)(received | (uint8_t)(1U << bit));
        }
        C5_Ps2Hal_DelayUs(hal, C5_PS2_EDGE_DELAY_US);
    }
    return received;
}

void C5_Ps2Hal_Init(C5_Ps2Hal *hal)
{
    if (hal != NULL)
    {
        hal->cycles_per_us = 0U;
        hal->active = 0U;
    }
}

int C5_Ps2Hal_Enter(void *context)
{
    C5_Ps2Hal *hal;
    GPIO_InitTypeDef gpio;

    hal = (C5_Ps2Hal *)context;
    if (hal == NULL)
    {
        return -1;
    }

    __HAL_RCC_AFIO_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_AFIO_REMAP_SWJ_DISABLE();
    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_OUTPUT_PINS, GPIO_PIN_SET);

    gpio.Pin = C5_PS2_OUTPUT_PINS;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(C5_PS2_GPIO_PORT, &gpio);

    gpio.Pin = C5_PS2_DAT_PIN;
    gpio.Mode = GPIO_MODE_INPUT;
    gpio.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(C5_PS2_GPIO_PORT, &gpio);

    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0U;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    hal->cycles_per_us = HAL_RCC_GetHCLKFreq() / 1000000U;
    hal->active = 1U;
    if (hal->cycles_per_us == 0U)
    {
        (void)C5_Ps2Hal_Exit(hal);
        return -1;
    }
    return 0;
}

int C5_Ps2Hal_Exit(void *context)
{
    C5_Ps2Hal *hal;

    hal = (C5_Ps2Hal *)context;
    if (hal == NULL)
    {
        return -1;
    }
    if (hal->active)
    {
        HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_OUTPUT_PINS, GPIO_PIN_SET);
        HAL_GPIO_DeInit(C5_PS2_GPIO_PORT, C5_PS2_ALL_PINS);
    }
    __HAL_AFIO_REMAP_SWJ_NOJTAG();
    hal->cycles_per_us = 0U;
    hal->active = 0U;
    return 0;
}

int C5_Ps2Hal_ReadFrame(void *context,
                        uint8_t frame[C5_PS2_FRAME_SIZE])
{
    static const uint8_t request[C5_PS2_FRAME_SIZE] =
        {0x01U, 0x42U, 0x00U, 0x00U, 0x00U,
         0x00U, 0x00U, 0x00U, 0x00U};
    C5_Ps2Hal *hal;
    uint8_t index;

    hal = (C5_Ps2Hal *)context;
    if ((hal == NULL) || (frame == NULL) || !hal->active)
    {
        return -1;
    }

    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CMD_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CLK_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_ATT_PIN, GPIO_PIN_RESET);
    C5_Ps2Hal_DelayUs(hal, C5_PS2_SELECT_DELAY_US);
    for (index = 0U; index < C5_PS2_FRAME_SIZE; ++index)
    {
        frame[index] = C5_Ps2Hal_Transfer(hal, request[index]);
    }
    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_ATT_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(C5_PS2_GPIO_PORT, C5_PS2_CMD_PIN, GPIO_PIN_SET);
    C5_Ps2Hal_DelayUs(hal, C5_PS2_SELECT_DELAY_US);
    return 0;
}
