#include "c5_host_protocol.h"

#include <string.h>

#include "c5_control_config.h"

static int16_t C5_HostProtocol_ReadI16(const uint8_t *data)
{
    uint16_t value;

    value = (uint16_t)data[0] | ((uint16_t)data[1] << 8);
    return (int16_t)value;
}

uint8_t C5_HostProtocol_Crc8(const uint8_t *data, size_t length)
{
    uint8_t crc;
    size_t index;
    uint8_t bit;

    if ((data == NULL) && (length != 0U))
    {
        return 0U;
    }
    crc = 0U;
    for (index = 0U; index < length; ++index)
    {
        crc ^= data[index];
        for (bit = 0U; bit < 8U; ++bit)
        {
            crc = (crc & 0x80U) ? (uint8_t)((crc << 1) ^ 0x07U) :
                                  (uint8_t)(crc << 1);
        }
    }
    return crc;
}

void C5_HostParser_Init(C5_HostParser *parser)
{
    if (parser != NULL)
    {
        memset(parser, 0, sizeof(*parser));
    }
}

int C5_HostParser_PushByte(C5_HostParser *parser,
                           uint8_t byte,
                           uint8_t frame_out[C5_HOST_FRAME_SIZE])
{
    if ((parser == NULL) || (frame_out == NULL))
    {
        return -1;
    }
    if (parser->length == 0U)
    {
        if (byte == C5_HOST_SYNC_0)
        {
            parser->frame[0] = byte;
            parser->length = 1U;
        }
        return 0;
    }
    if (parser->length == 1U)
    {
        if (byte == C5_HOST_SYNC_1)
        {
            parser->frame[1] = byte;
            parser->length = 2U;
        }
        else if (byte != C5_HOST_SYNC_0)
        {
            parser->length = 0U;
        }
        return 0;
    }

    parser->frame[parser->length] = byte;
    ++parser->length;
    if (parser->length < C5_HOST_FRAME_SIZE)
    {
        return 0;
    }
    memcpy(frame_out, parser->frame, C5_HOST_FRAME_SIZE);
    parser->length = 0U;
    return 1;
}

C5_HostResult C5_HostProtocol_DecodeCommand(
    const uint8_t frame[C5_HOST_FRAME_SIZE],
    C5_HostCommand *command)
{
    uint8_t type;
    int16_t vx;
    int16_t vy;
    int16_t wz;

    if ((frame == NULL) || (command == NULL) ||
        (frame[0] != C5_HOST_SYNC_0) ||
        (frame[1] != C5_HOST_SYNC_1))
    {
        return C5_HOST_RESULT_BAD_PAYLOAD;
    }
    if (C5_HostProtocol_Crc8(&frame[2], 8U) != frame[10])
    {
        return C5_HOST_RESULT_BAD_CRC;
    }

    type = frame[2];
    vx = C5_HostProtocol_ReadI16(&frame[4]);
    vy = C5_HostProtocol_ReadI16(&frame[6]);
    wz = C5_HostProtocol_ReadI16(&frame[8]);
    if ((type != C5_HOST_COMMAND_ARM) &&
        (type != C5_HOST_COMMAND_TWIST) &&
        (type != C5_HOST_COMMAND_STOP) &&
        (type != C5_HOST_COMMAND_QUERY))
    {
        return C5_HOST_RESULT_BAD_TYPE;
    }
    if (type == C5_HOST_COMMAND_TWIST)
    {
        if ((vx < -C5_HOST_AXIS_LIMIT) || (vx > C5_HOST_AXIS_LIMIT) ||
            (vy < -C5_HOST_AXIS_LIMIT) || (vy > C5_HOST_AXIS_LIMIT) ||
            (wz < -C5_HOST_AXIS_LIMIT) || (wz > C5_HOST_AXIS_LIMIT))
        {
            return C5_HOST_RESULT_BAD_PAYLOAD;
        }
    }
    else if ((vx != 0) || (vy != 0) || (wz != 0))
    {
        return C5_HOST_RESULT_BAD_PAYLOAD;
    }

    command->type = (C5_HostCommandType)type;
    command->sequence = frame[3];
    command->vx = vx;
    command->vy = vy;
    command->wz = wz;
    return C5_HOST_RESULT_OK;
}

size_t C5_HostProtocol_FormatStatus(const C5_HostStatus *status,
                                    uint8_t *frame,
                                    size_t capacity)
{
    if ((status == NULL) || (frame == NULL) ||
        (capacity < C5_HOST_FRAME_SIZE))
    {
        return 0U;
    }
    frame[0] = C5_HOST_SYNC_0;
    frame[1] = C5_HOST_SYNC_1;
    frame[2] = 0x80U;
    frame[3] = status->sequence;
    frame[4] = (uint8_t)status->result;
    frame[5] = status->mode;
    frame[6] = status->host_state;
    frame[7] = status->motion_state;
    frame[8] = (uint8_t)(status->error_count & 0xFFU);
    frame[9] = (uint8_t)((status->error_count >> 8) & 0xFFU);
    frame[10] = C5_HostProtocol_Crc8(&frame[2], 8U);
    return C5_HOST_FRAME_SIZE;
}
