#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "c5_mecanum.h"
#include "c5_motion.h"

typedef struct
{
    char last_frame[C5_MOTOR_GROUP_FRAME_SIZE + 1U];
    size_t last_length;
    unsigned int write_count;
    unsigned int failures_remaining;
} MockTransport;

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

int main(void)
{
    TestProtocol();
    TestMecanum();
    TestTimeoutAndFaultStop();
    TestTickWraparound();
    puts("c5_motion_tests: PASS");
    return 0;
}
