#ifndef C5_CONTROL_H
#define C5_CONTROL_H

#include <stdint.h>

#include "c5_ps2.h"
#include "c5_remote.h"

typedef int (*C5_ControlReadFrame)(void *context,
                                   uint8_t frame[C5_PS2_FRAME_SIZE]);
typedef int (*C5_ControlModeChange)(void *context);

typedef enum
{
    C5_CONTROL_DEBUG = 0,
    C5_CONTROL_PS2
} C5_ControlState;

typedef struct
{
    C5_Remote remote;
    C5_ControlReadFrame read_frame;
    void *read_context;
    C5_ControlModeChange enter_ps2;
    void *enter_context;
    C5_ControlModeChange exit_ps2;
    void *exit_context;
    C5_ControlState state;
    uint32_t key_change_ms;
    uint32_t key_press_ms;
    uint32_t next_poll_ms;
    uint8_t raw_key_pressed;
    uint8_t stable_key_pressed;
    uint8_t long_press_handled;
} C5_Control;

void C5_Control_Init(C5_Control *control,
                     C5_Motion *motion,
                     C5_ControlReadFrame read_frame,
                     void *read_context,
                     C5_ControlModeChange enter_ps2,
                     void *enter_context,
                     C5_ControlModeChange exit_ps2,
                     void *exit_context,
                     int key_pressed,
                     uint32_t now_ms);
void C5_Control_Service(C5_Control *control,
                        int key_pressed,
                        uint32_t now_ms);
C5_ControlState C5_Control_GetState(const C5_Control *control);
C5_RemoteState C5_Control_GetRemoteState(const C5_Control *control);

#endif
