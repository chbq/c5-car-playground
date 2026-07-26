#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "c5_control.h"
#include "c5_host_control.h"
#include "c5_host_protocol.h"
#include "c5_host_uart_hal.h"
#include "c5_mecanum.h"
#include "c5_motion.h"
#include "c5_motion_config.h"
#include "c5_ps2.h"
#include "c5_remote.h"

typedef struct
{
    char last_frame[C5_MOTOR_GROUP_FRAME_SIZE + 1U];
    size_t last_length;
    unsigned int write_count;
    unsigned int failures_remaining;
} MockTransport;

typedef struct
{
    uint8_t frame[C5_PS2_FRAME_SIZE];
    unsigned int enter_count;
    unsigned int exit_count;
    unsigned int read_count;
} MockControlIo;

static HAL_StatusTypeDef mock_uart_receive_result = HAL_OK;
static HAL_StatusTypeDef mock_uart_transmit_result = HAL_OK;
static unsigned int mock_uart_receive_count;
static unsigned int mock_uart_transmit_count;
static uint8_t mock_uart_last_tx[C5_HOST_FRAME_SIZE];

HAL_StatusTypeDef HAL_UART_Receive_IT(UART_HandleTypeDef *uart,
                                      uint8_t *data,
                                      uint16_t size)
{
    assert(uart != NULL);
    assert(data != NULL);
    assert(size == 1U);
    ++mock_uart_receive_count;
    return mock_uart_receive_result;
}

HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *uart,
                                    const uint8_t *data,
                                    uint16_t size,
                                    uint32_t timeout)
{
    assert(uart != NULL);
    assert(data != NULL);
    assert(size == C5_HOST_FRAME_SIZE);
    assert(timeout == C5_HOST_UART_TX_TIMEOUT_MS);
    memcpy(mock_uart_last_tx, data, size);
    ++mock_uart_transmit_count;
    return mock_uart_transmit_result;
}

static int MockWrite(void *context, const uint8_t *data, size_t length)
{
    MockTransport *mock;

    mock = (MockTransport *)context;
    ++mock->write_count;
    if (mock->failures_remaining > 0U)
    {
        --mock->failures_remaining;
        return -1;
    }
    assert(length < sizeof(mock->last_frame));
    memcpy(mock->last_frame, data, length);
    mock->last_frame[length] = '\0';
    mock->last_length = length;
    return 0;
}

static void MakeNeutralPs2Frame(uint8_t frame[C5_PS2_FRAME_SIZE])
{
    static const uint8_t neutral[C5_PS2_FRAME_SIZE] =
        {0xFFU, 0x73U, 0x5AU, 0xFFU, 0xFFU,
         0x80U, 0x80U, 0x80U, 0x80U};

    memcpy(frame, neutral, sizeof(neutral));
}

static int MockEnterPs2(void *context)
{
    MockControlIo *io;

    io = (MockControlIo *)context;
    ++io->enter_count;
    return 0;
}

static int MockExitPs2(void *context)
{
    MockControlIo *io;

    io = (MockControlIo *)context;
    ++io->exit_count;
    return 0;
}

static int MockReadPs2(void *context, uint8_t frame[C5_PS2_FRAME_SIZE])
{
    MockControlIo *io;

    io = (MockControlIo *)context;
    ++io->read_count;
    memcpy(frame, io->frame, C5_PS2_FRAME_SIZE);
    return 0;
}

static void MakeHostFrame(uint8_t type, uint8_t sequence,
                          int16_t vx, int16_t vy, int16_t wz,
                          uint8_t frame[C5_HOST_FRAME_SIZE])
{
    frame[0] = C5_HOST_SYNC_0;
    frame[1] = C5_HOST_SYNC_1;
    frame[2] = type;
    frame[3] = sequence;
    frame[4] = (uint8_t)((uint16_t)vx & 0xFFU);
    frame[5] = (uint8_t)(((uint16_t)vx >> 8) & 0xFFU);
    frame[6] = (uint8_t)((uint16_t)vy & 0xFFU);
    frame[7] = (uint8_t)(((uint16_t)vy >> 8) & 0xFFU);
    frame[8] = (uint8_t)((uint16_t)wz & 0xFFU);
    frame[9] = (uint8_t)(((uint16_t)wz >> 8) & 0xFFU);
    frame[10] = C5_HostProtocol_Crc8(&frame[2], 8U);
}

static C5_HostCommand MakeHostCommand(C5_HostCommandType type,
                                      uint8_t sequence,
                                      int16_t vx,
                                      int16_t vy,
                                      int16_t wz)
{
    C5_HostCommand command;

    command.type = type;
    command.sequence = sequence;
    command.vx = vx;
    command.vy = vy;
    command.wz = wz;
    return command;
}

static void TestHostProtocol(void)
{
    static const uint8_t arm_frame[C5_HOST_FRAME_SIZE] =
        {0xA5U, 0x5AU, 0x01U, 0x10U, 0x00U, 0x00U,
         0x00U, 0x00U, 0x00U, 0x00U, 0xC0U};
    static const uint8_t twist_frame[C5_HOST_FRAME_SIZE] =
        {0xA5U, 0x5AU, 0x02U, 0x22U, 0x64U, 0x00U,
         0x38U, 0xFFU, 0x32U, 0x00U, 0x36U};
    C5_HostParser parser;
    C5_HostCommand command;
    C5_HostStatus status;
    uint8_t frame[C5_HOST_FRAME_SIZE];
    unsigned int index;
    int emitted;

    assert(C5_HostProtocol_Crc8(&arm_frame[2], 8U) == 0xC0U);
    assert(C5_HostProtocol_DecodeCommand(arm_frame, &command) ==
           C5_HOST_RESULT_OK);
    assert(command.type == C5_HOST_COMMAND_ARM);
    assert(command.sequence == 0x10U);
    assert(C5_HostProtocol_DecodeCommand(twist_frame, &command) ==
           C5_HOST_RESULT_OK);
    assert(command.vx == 100);
    assert(command.vy == -200);
    assert(command.wz == 50);

    memcpy(frame, twist_frame, sizeof(frame));
    frame[10] ^= 0x01U;
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_BAD_CRC);
    MakeHostFrame(0x7FU, 1U, 0, 0, 0, frame);
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_BAD_TYPE);
    MakeHostFrame(C5_HOST_COMMAND_TWIST, 2U, 1001, 0, 0, frame);
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_BAD_PAYLOAD);
    MakeHostFrame(C5_HOST_COMMAND_TWIST, 2U, -1001, 0, 0, frame);
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_BAD_PAYLOAD);
    MakeHostFrame(C5_HOST_COMMAND_TWIST, 2U, -1000, 1000, -1000, frame);
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_OK);
    assert(command.vx == -1000);
    assert(command.vy == 1000);
    assert(command.wz == -1000);
    MakeHostFrame(C5_HOST_COMMAND_ARM, 3U, 1, 0, 0, frame);
    assert(C5_HostProtocol_DecodeCommand(frame, &command) ==
           C5_HOST_RESULT_BAD_PAYLOAD);

    C5_HostParser_Init(&parser);
    assert(C5_HostParser_PushByte(&parser, 0x00U, frame) == 0);
    assert(C5_HostParser_PushByte(&parser, 0xA5U, frame) == 0);
    assert(C5_HostParser_PushByte(&parser, 0xA5U, frame) == 0);
    emitted = 0;
    for (index = 1U; index < C5_HOST_FRAME_SIZE; ++index)
    {
        emitted += C5_HostParser_PushByte(&parser, arm_frame[index], frame);
    }
    assert(emitted == 1);
    assert(memcmp(frame, arm_frame, sizeof(frame)) == 0);

    emitted = 0;
    for (index = 0U; index < C5_HOST_FRAME_SIZE; ++index)
    {
        emitted += C5_HostParser_PushByte(&parser, arm_frame[index], frame);
    }
    assert(emitted == 1);
    assert(memcmp(frame, arm_frame, sizeof(frame)) == 0);
    emitted = 0;
    for (index = 0U; index < C5_HOST_FRAME_SIZE; ++index)
    {
        emitted += C5_HostParser_PushByte(&parser, twist_frame[index], frame);
    }
    assert(emitted == 1);
    assert(memcmp(frame, twist_frame, sizeof(frame)) == 0);

    status.sequence = 0x10U;
    status.result = C5_HOST_RESULT_OK;
    status.mode = 0U;
    status.host_state = 1U;
    status.motion_state = 1U;
    status.error_count = 0U;
    assert(C5_HostProtocol_FormatStatus(&status, frame, sizeof(frame)) ==
           C5_HOST_FRAME_SIZE);
    assert(frame[2] == 0x80U);
    assert(frame[10] == 0x11U);
}

static void FeedHostUartFrame(C5_HostUartHal *hal,
                              const uint8_t frame[C5_HOST_FRAME_SIZE])
{
    unsigned int index;

    for (index = 0U; index < C5_HOST_FRAME_SIZE; ++index)
    {
        hal->rx_byte = frame[index];
        C5_HostUartHal_RxCompleteIsr(hal);
    }
}

static void TestHostUartQueueAndFaults(void)
{
    UART_HandleTypeDef uart = {0};
    C5_HostUartHal hal;
    C5_HostRxEvent event;
    C5_HostResult fault;
    C5_HostStatus status;
    uint8_t frame[C5_HOST_FRAME_SIZE];
    unsigned int sequence;
    unsigned int event_count;

    mock_uart_receive_result = HAL_OK;
    mock_uart_transmit_result = HAL_OK;
    mock_uart_receive_count = 0U;
    mock_uart_transmit_count = 0U;
    uart.RxState = HAL_UART_STATE_READY;
    C5_HostUartHal_Init(&hal, &uart);
    assert(C5_HostUartHal_Start(&hal) == 0);

    for (sequence = 1U; sequence <= C5_HOST_EVENT_QUEUE_SIZE; ++sequence)
    {
        MakeHostFrame(C5_HOST_COMMAND_QUERY, (uint8_t)sequence,
                      0, 0, 0, frame);
        FeedHostUartFrame(&hal, frame);
    }
    assert(C5_HostUartHal_ConsumeFault(&hal, &fault) == 1);
    assert(fault == C5_HOST_RESULT_RX_OVERFLOW);
    assert(C5_HostUartHal_GetErrorCount(&hal) == 1U);
    event_count = 0U;
    while (C5_HostUartHal_PopEvent(&hal, &event) == 1)
    {
        ++event_count;
        assert(event.sequence == event_count);
        assert(event.result == C5_HOST_RESULT_OK);
    }
    assert(event_count == C5_HOST_EVENT_QUEUE_SIZE - 1U);

    C5_HostUartHal_ErrorIsr(&hal);
    assert(C5_HostUartHal_ConsumeFault(&hal, &fault) == 1);
    assert(fault == C5_HOST_RESULT_UART_ERROR);
    assert(C5_HostUartHal_GetErrorCount(&hal) == 2U);

    status.sequence = 9U;
    status.result = C5_HOST_RESULT_OK;
    status.mode = 0U;
    status.host_state = 0U;
    status.motion_state = 1U;
    status.error_count = 2U;
    assert(C5_HostUartHal_SendStatus(&hal, &status) == 0);
    assert(mock_uart_transmit_count == 1U);
    assert(mock_uart_last_tx[3] == 9U);
    assert(C5_HostProtocol_Crc8(&mock_uart_last_tx[2], 8U) ==
           mock_uart_last_tx[10]);
    assert(mock_uart_receive_count ==
           (1U + C5_HOST_EVENT_QUEUE_SIZE * C5_HOST_FRAME_SIZE + 1U));
}

static void TestHostControlSafety(void)
{
    MockTransport transport = {{0}, 0U, 0U, 0U};
    MockControlIo io = {{0}, 0U, 0U, 0U};
    C5_Motion motion;
    C5_Control control;
    C5_HostCommand command;
    C5_HostStatus status;

    MakeNeutralPs2Frame(io.frame);
    assert(C5_Motion_Init(&motion, MockWrite, &transport, NULL, 0U) == 0);
    C5_Control_Init(&control, &motion,
                    MockReadPs2, &io,
                    MockEnterPs2, &io,
                    MockExitPs2, &io,
                    0, 0U);

    command = MakeHostCommand(C5_HOST_COMMAND_TWIST, 1U, 100, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 10U) ==
           C5_HOST_RESULT_NOT_ARMED);
    command = MakeHostCommand(C5_HOST_COMMAND_ARM, 2U, 0, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 20U) ==
           C5_HOST_RESULT_OK);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_ARMED);

    command = MakeHostCommand(C5_HOST_COMMAND_TWIST, 3U, 100, -50, 25);
    assert(C5_Control_ProcessHostCommand(&control, &command, 30U) ==
           C5_HOST_RESULT_OK);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);
    C5_Motion_Service(&motion, 179U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);
    C5_Motion_Service(&motion, 180U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_ARMED);
    C5_Control_Service(&control, 0, 229U);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_ARMED);
    C5_Control_Service(&control, 0, 230U);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_DISARMED);

    command = MakeHostCommand(C5_HOST_COMMAND_ARM, 4U, 0, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 300U) ==
           C5_HOST_RESULT_OK);
    command = MakeHostCommand(C5_HOST_COMMAND_TWIST, 5U, 0, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 310U) ==
           C5_HOST_RESULT_OK);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_ARMED);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);

    assert(C5_Control_HostFault(&control, 320U) == C5_HOST_RESULT_OK);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_DISARMED);
    C5_Control_GetHostStatus(&control, 5U, C5_HOST_RESULT_BAD_CRC,
                             7U, &status);
    assert(status.sequence == 5U);
    assert(status.result == C5_HOST_RESULT_BAD_CRC);
    assert(status.mode == C5_CONTROL_DEBUG);
    assert(status.host_state == C5_HOST_LINK_DISARMED);
    assert(status.motion_state == C5_MOTION_STOPPED);
    assert(status.error_count == 7U);
}

static void TestHostTimeoutWraparound(void)
{
    MockTransport transport = {{0}, 0U, 0U, 0U};
    C5_Motion motion;
    C5_HostControl host;
    C5_HostCommand command;

    assert(C5_Motion_Init(&motion, MockWrite, &transport, NULL,
                          0xFFFFFF00U) == 0);
    C5_HostControl_Init(&host, &motion, 0xFFFFFF00U);
    command = MakeHostCommand(C5_HOST_COMMAND_ARM, 1U, 0, 0, 0);
    assert(C5_HostControl_Process(&host, &command, 0xFFFFFFF0U) ==
           C5_HOST_RESULT_OK);
    C5_HostControl_Service(&host, 0x000000B7U);
    assert(C5_HostControl_GetState(&host) == C5_HOST_LINK_ARMED);
    C5_HostControl_Service(&host, 0x000000B8U);
    assert(C5_HostControl_GetState(&host) == C5_HOST_LINK_DISARMED);
}

static void TestProtocol(void)
{
    char frame[C5_MOTOR_GROUP_FRAME_SIZE + 1U];
    C5_WheelSpeeds speeds = {{100, 200, -300, -400}};
    size_t length;

    length = C5_MotorProtocol_FormatStop(frame, sizeof(frame));
    assert(length == C5_MOTOR_SINGLE_FRAME_SIZE);
    assert(strcmp(frame, "#255P1500T0000!") == 0);

    length = C5_MotorProtocol_FormatWheels(
        &C5_MOTOR_LAYOUT_VENDOR_DEFAULT, &speeds, frame, sizeof(frame));
    assert(length == C5_MOTOR_GROUP_FRAME_SIZE);
    assert(strcmp(frame,
        "{#006P1600T0000!#007P1300T0000!#008P1200T0000!#009P1900T0000!}") == 0);

    assert(C5_MotorProtocol_SpeedToPulse(1200, 1) == 2500U);
    assert(C5_MotorProtocol_SpeedToPulse(-1200, 1) == 500U);
    assert(C5_MotorProtocol_FormatSingleRaw(6U, 499U, 0U,
                                             frame, sizeof(frame)) == 0U);
}

static void AssertSpeeds(const C5_WheelSpeeds *speeds,
                         int lf, int rf, int lr, int rr)
{
    assert(speeds->value[C5_WHEEL_LEFT_FRONT] == lf);
    assert(speeds->value[C5_WHEEL_RIGHT_FRONT] == rf);
    assert(speeds->value[C5_WHEEL_LEFT_REAR] == lr);
    assert(speeds->value[C5_WHEEL_RIGHT_REAR] == rr);
}

static void TestMecanum(void)
{
    C5_WheelSpeeds speeds;

    C5_Mecanum_Mix(100, 0, 0, 1000, &speeds);
    AssertSpeeds(&speeds, 100, 100, 100, 100);

    C5_Mecanum_Mix(0, 100, 0, 1000, &speeds);
    AssertSpeeds(&speeds, 100, -100, -100, 100);

    C5_Mecanum_Mix(0, 0, 100, 1000, &speeds);
    AssertSpeeds(&speeds, 100, -100, 100, -100);

    C5_Mecanum_Mix(1000, 1000, 1000, 1000, &speeds);
    AssertSpeeds(&speeds, 1000, -333, 333, 333);
}

static void TestTimeoutAndFaultStop(void)
{
    MockTransport mock = {{0}, 0U, 0U, 0U};
    C5_Motion motion;

    assert(C5_Motion_Init(&motion, MockWrite, &mock, NULL, 1000U) == 0);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);
    assert(strcmp(mock.last_frame, "#255P1500T0000!") == 0);

    assert(C5_Motion_Forward(&motion, 100, 250U, 1000U) == 0);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);
    assert(strcmp(mock.last_frame,
        "{#006P1600T0000!#007P1400T0000!#008P1600T0000!#009P1400T0000!}") == 0);

    assert(C5_Motion_Backward(&motion, -100, 250U, 1100U) == 0);
    assert(strcmp(mock.last_frame,
        "{#006P1400T0000!#007P1600T0000!#008P1400T0000!#009P1600T0000!}") == 0);

    C5_Motion_Service(&motion, 1349U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);
    C5_Motion_Service(&motion, 1350U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);
    assert(strcmp(mock.last_frame, "#255P1500T0000!") == 0);

    mock.failures_remaining = 2U;
    assert(C5_Motion_StrafeRight(&motion, 200, 200U, 2000U) != 0);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_FAULT);
    assert(motion.stop_confirmed == 0U);

    C5_Motion_Service(&motion, 2099U);
    assert(motion.stop_confirmed == 0U);
    C5_Motion_Service(&motion, 2100U);
    assert(motion.stop_confirmed == 1U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_FAULT);
    assert(strcmp(mock.last_frame, "#255P1500T0000!") == 0);

    assert(C5_Motion_ClearFault(&motion, 2200U) == 0);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);
}

static void TestTickWraparound(void)
{
    MockTransport mock = {{0}, 0U, 0U, 0U};
    C5_Motion motion;

    assert(C5_Motion_Init(&motion, MockWrite, &mock, NULL, 0xFFFFFFF0U) == 0);
    assert(C5_Motion_Forward(&motion, 100, 32U, 0xFFFFFFF0U) == 0);
    C5_Motion_Service(&motion, 0x0000000FU);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);
    C5_Motion_Service(&motion, 0x00000010U);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_STOPPED);
}

static void TestPs2DecodeAndMapping(void)
{
    uint8_t frame[C5_PS2_FRAME_SIZE];
    C5_Ps2State state;
    int16_t vx;
    int16_t vy;
    int16_t wz;

    MakeNeutralPs2Frame(frame);
    assert(C5_Ps2_Decode(frame, sizeof(frame), &state) == 0);
    assert(C5_Ps2_IsNeutral(&state, 8));
    assert(!C5_Ps2_DeadmanPressed(&state));

    frame[4] = (uint8_t)(frame[4] & 0xFBU);
    frame[5] = 0U;
    frame[7] = 255U;
    frame[8] = 0U;
    assert(C5_Ps2_Decode(frame, sizeof(frame), &state) == 0);
    assert(C5_Ps2_DeadmanPressed(&state));
    C5_Ps2_MapTwist(&state, 8, C5_MOTION_OUTPUT_LIMIT,
                    &vx, &vy, &wz);
    assert(vx == C5_MOTION_OUTPUT_LIMIT);
    assert(vy == C5_MOTION_OUTPUT_LIMIT);
    assert(wz == -C5_MOTION_OUTPUT_LIMIT);

    frame[1] = 0x41U;
    assert(C5_Ps2_Decode(frame, sizeof(frame), &state) != 0);
}

static void TestRemoteSafety(void)
{
    MockTransport mock = {{0}, 0U, 0U, 0U};
    C5_Motion motion;
    C5_Remote remote;
    uint8_t frame[C5_PS2_FRAME_SIZE];

    assert(C5_Motion_Init(&motion, MockWrite, &mock, NULL, 0U) == 0);
    C5_Remote_Init(&remote, &motion, 0U);
    MakeNeutralPs2Frame(frame);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 10U) == 0);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 20U) == 0);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_DISARMED);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 30U) == 0);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_READY);

    frame[4] = (uint8_t)(frame[4] & 0xFBU);
    frame[8] = 96U;
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 50U) == 0);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_ACTIVE);
    assert(C5_Motion_GetState(&motion) == C5_MOTION_MOVING);

    MakeNeutralPs2Frame(frame);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 75U) == 0);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_READY);
    assert(strcmp(mock.last_frame, "#255P1500T0000!") == 0);

    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 80U) == 0);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 90U) == 0);
    frame[4] = (uint8_t)(frame[4] & 0xF7U);
    frame[7] = 160U;
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 100U) == 0);
    C5_Remote_Service(&remote, 249U);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_ACTIVE);
    C5_Remote_Service(&remote, 250U);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_DISARMED);
    assert(strcmp(mock.last_frame, "#255P1500T0000!") == 0);

    frame[1] = 0x41U;
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 300U) != 0);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_DISARMED);
}

static void TestRemoteTimeoutWraparound(void)
{
    MockTransport mock = {{0}, 0U, 0U, 0U};
    C5_Motion motion;
    C5_Remote remote;
    uint8_t frame[C5_PS2_FRAME_SIZE];

    assert(C5_Motion_Init(&motion, MockWrite, &mock, NULL, 0xFFFFFF00U) == 0);
    C5_Remote_Init(&remote, &motion, 0xFFFFFF00U);
    MakeNeutralPs2Frame(frame);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 0xFFFFFF10U) == 0);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 0xFFFFFF20U) == 0);
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 0xFFFFFF30U) == 0);
    frame[4] = (uint8_t)(frame[4] & 0xFBU);
    frame[8] = 96U;
    assert(C5_Remote_ProcessFrame(&remote, frame, sizeof(frame), 0xFFFFFFF0U) == 0);
    C5_Remote_Service(&remote, 0x00000085U);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_ACTIVE);
    C5_Remote_Service(&remote, 0x00000086U);
    assert(C5_Remote_GetState(&remote) == C5_REMOTE_DISARMED);
}

static void TestControlModeSwitch(void)
{
    MockTransport transport = {{0}, 0U, 0U, 0U};
    MockControlIo io = {{0}, 0U, 0U, 0U};
    C5_Motion motion;
    C5_Control control;
    C5_HostCommand command;

    MakeNeutralPs2Frame(io.frame);
    assert(C5_Motion_Init(&motion, MockWrite, &transport, NULL, 0U) == 0);
    C5_Control_Init(&control, &motion,
                    MockReadPs2, &io,
                    MockEnterPs2, &io,
                    MockExitPs2, &io,
                    0, 0U);

    command = MakeHostCommand(C5_HOST_COMMAND_ARM, 1U, 0, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 1U) ==
           C5_HOST_RESULT_OK);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_ARMED);

    C5_Control_Service(&control, 1, 10U);
    C5_Control_Service(&control, 1, 40U);
    C5_Control_Service(&control, 1, 2039U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_DEBUG);
    C5_Control_Service(&control, 1, 2040U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_PS2);
    assert(C5_Control_GetHostState(&control) == C5_HOST_LINK_DISARMED);
    assert(io.enter_count == 1U);

    command = MakeHostCommand(C5_HOST_COMMAND_TWIST, 2U, 100, 0, 0);
    assert(C5_Control_ProcessHostCommand(&control, &command, 2041U) ==
           C5_HOST_RESULT_MODE_DENIED);

    C5_Control_Service(&control, 0, 2050U);
    C5_Control_Service(&control, 0, 2080U);
    assert(io.read_count == 1U);
    C5_Control_Service(&control, 1, 2100U);
    C5_Control_Service(&control, 1, 2130U);
    assert(C5_Control_GetRemoteState(&control) == C5_REMOTE_DISARMED);
    C5_Control_Service(&control, 1, 4130U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_DEBUG);
    assert(io.exit_count == 1U);
    assert(C5_Control_ProcessHostCommand(&control, &command, 4131U) ==
           C5_HOST_RESULT_NOT_ARMED);
}

int main(void)
{
    TestProtocol();
    TestHostProtocol();
    TestHostUartQueueAndFaults();
    TestMecanum();
    TestTimeoutAndFaultStop();
    TestTickWraparound();
    TestPs2DecodeAndMapping();
    TestRemoteSafety();
    TestRemoteTimeoutWraparound();
    TestHostControlSafety();
    TestHostTimeoutWraparound();
    TestControlModeSwitch();
    puts("c5_motion_tests: PASS");
    return 0;
}
