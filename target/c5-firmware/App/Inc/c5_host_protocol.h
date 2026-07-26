#ifndef C5_HOST_PROTOCOL_H
#define C5_HOST_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define C5_HOST_FRAME_SIZE 11U
#define C5_HOST_SYNC_0     0xA5U
#define C5_HOST_SYNC_1     0x5AU

typedef enum
{
    C5_HOST_COMMAND_ARM = 0x01,
    C5_HOST_COMMAND_TWIST = 0x02,
    C5_HOST_COMMAND_STOP = 0x03,
    C5_HOST_COMMAND_QUERY = 0x04
} C5_HostCommandType;

typedef enum
{
    C5_HOST_RESULT_OK = 0,
    C5_HOST_RESULT_BAD_CRC,
    C5_HOST_RESULT_BAD_TYPE,
    C5_HOST_RESULT_BAD_PAYLOAD,
    C5_HOST_RESULT_MODE_DENIED,
    C5_HOST_RESULT_NOT_ARMED,
    C5_HOST_RESULT_MOTION_FAULT,
    C5_HOST_RESULT_RX_OVERFLOW,
    C5_HOST_RESULT_UART_ERROR
} C5_HostResult;

typedef enum
{
    C5_HOST_LINK_DISARMED = 0,
    C5_HOST_LINK_ARMED
} C5_HostLinkState;

typedef struct
{
    C5_HostCommandType type;
    uint8_t sequence;
    int16_t vx;
    int16_t vy;
    int16_t wz;
} C5_HostCommand;

typedef struct
{
    uint8_t sequence;
    C5_HostResult result;
    uint8_t mode;
    uint8_t host_state;
    uint8_t motion_state;
    uint16_t error_count;
} C5_HostStatus;

typedef struct
{
    uint8_t frame[C5_HOST_FRAME_SIZE];
    uint8_t length;
} C5_HostParser;

/**
 * @brief  Calculate CRC-8/ATM without a lookup table.
 * @param[in] data    Input bytes.
 * @param[in] length  Number of bytes; zero is allowed.
 * @return CRC with polynomial 0x07, init 0x00 and xorout 0x00.
 */
uint8_t C5_HostProtocol_Crc8(const uint8_t *data, size_t length);

/**
 * @brief  Reset the fixed-frame stream parser.
 * @param[out] parser  Parser object.
 */
void C5_HostParser_Init(C5_HostParser *parser);

/**
 * @brief  Consume one byte and emit a complete 11-byte candidate frame.
 * @param[in,out] parser     Parser object.
 * @param[in]     byte       Next UART byte.
 * @param[out]    frame_out  Complete candidate when the return value is 1.
 * @retval 1   A complete candidate was copied to frame_out.
 * @retval 0   More bytes are required or garbage was discarded.
 * @retval -1  Invalid input.
 */
int C5_HostParser_PushByte(C5_HostParser *parser,
                           uint8_t byte,
                           uint8_t frame_out[C5_HOST_FRAME_SIZE]);

/**
 * @brief  Validate and decode one HOST command frame.
 * @param[in]  frame    Fixed 11-byte command frame.
 * @param[out] command  Decoded command on success.
 * @return Protocol result code; C5_HOST_RESULT_OK means success.
 */
C5_HostResult C5_HostProtocol_DecodeCommand(
    const uint8_t frame[C5_HOST_FRAME_SIZE],
    C5_HostCommand *command);

/**
 * @brief  Format one fixed 11-byte STM32 status frame.
 * @param[in]  status    Status fields.
 * @param[out] frame     Output buffer.
 * @param[in]  capacity  Must be at least C5_HOST_FRAME_SIZE.
 * @return C5_HOST_FRAME_SIZE on success, otherwise zero.
 */
size_t C5_HostProtocol_FormatStatus(const C5_HostStatus *status,
                                    uint8_t *frame,
                                    size_t capacity);

#endif
