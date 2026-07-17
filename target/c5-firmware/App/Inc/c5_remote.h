#ifndef C5_REMOTE_H
#define C5_REMOTE_H

#include <stddef.h>
#include <stdint.h>

#include "c5_motion.h"

typedef enum
{
    C5_REMOTE_DISARMED = 0,
    C5_REMOTE_READY,
    C5_REMOTE_ACTIVE
} C5_RemoteState;

typedef struct
{
    C5_Motion *motion;
    C5_RemoteState state;
    uint32_t last_frame_ms;
    uint8_t neutral_frames;
    uint8_t have_valid_frame;
} C5_Remote;

void C5_Remote_Init(C5_Remote *remote, C5_Motion *motion, uint32_t now_ms);
int C5_Remote_ProcessFrame(C5_Remote *remote,
                           const uint8_t *frame,
                           size_t length,
                           uint32_t now_ms);
int C5_Remote_ForceStop(C5_Remote *remote, uint32_t now_ms);
void C5_Remote_Service(C5_Remote *remote, uint32_t now_ms);
C5_RemoteState C5_Remote_GetState(const C5_Remote *remote);

#endif
