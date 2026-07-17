#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "c5_control.h"
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

    MakeNeutralPs2Frame(io.frame);
    assert(C5_Motion_Init(&motion, MockWrite, &transport, NULL, 0U) == 0);
    C5_Control_Init(&control, &motion,
                    MockReadPs2, &io,
                    MockEnterPs2, &io,
                    MockExitPs2, &io,
                    0, 0U);

    C5_Control_Service(&control, 1, 10U);
    C5_Control_Service(&control, 1, 40U);
    C5_Control_Service(&control, 1, 2039U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_DEBUG);
    C5_Control_Service(&control, 1, 2040U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_PS2);
    assert(io.enter_count == 1U);

    C5_Control_Service(&control, 0, 2050U);
    C5_Control_Service(&control, 0, 2080U);
    assert(io.read_count == 1U);
    C5_Control_Service(&control, 1, 2100U);
    C5_Control_Service(&control, 1, 2130U);
    assert(C5_Control_GetRemoteState(&control) == C5_REMOTE_DISARMED);
    C5_Control_Service(&control, 1, 4130U);
    assert(C5_Control_GetState(&control) == C5_CONTROL_DEBUG);
    assert(io.exit_count == 1U);
}

int main(void)
{
    TestProtocol();
    TestMecanum();
    TestTimeoutAndFaultStop();
    TestTickWraparound();
    TestPs2DecodeAndMapping();
    TestRemoteSafety();
    TestRemoteTimeoutWraparound();
    TestControlModeSwitch();
    puts("c5_motion_tests: PASS");
    return 0;
}
