/* ZIRH-2 memory map and register definitions (must match src/zirh_rom.v
 * header comment and the bus slot decode in src/zirh_bus.v). */
#ifndef ZIRH_H
#define ZIRH_H

#include <stdint.h>

#define REG32(a) (*(volatile uint32_t *)(a))

#define RAM_BASE   0x00001000u
#define RAM_BYTES  64u

#define UART_BASE  0x00002000u
#define UART_STATUS REG32(UART_BASE + 0x0)
#define UART_TXDATA REG32(UART_BASE + 0x4)
#define UART_RXDATA REG32(UART_BASE + 0x8)
#define UART_BAUD   REG32(UART_BASE + 0xC)

#define UART_TX_FREE  (1u << 0)
#define UART_RX_AVAIL (1u << 1)

#define HK_BASE    0x00003000u
#define HK_SIG     REG32(HK_BASE + 0x00)
#define HK_CTRL    REG32(HK_BASE + 0x04)
#define HK_CPU_SIG REG32(HK_BASE + 0x08)
#define HK_INJECT  REG32(HK_BASE + 0x0C)
#define HK_ENV_RO  REG32(HK_BASE + 0x38)
#define HK_ENV_SB  REG32(HK_BASE + 0x3C)
#define ENV_RO_BUSY (1u << 31)

#endif
