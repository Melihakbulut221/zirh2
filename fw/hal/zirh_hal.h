/* ZIRH HAL - the driver layer over the generated register map
 * (PROGRAM.md F29). Addresses come from fw/zirh_regs.h, which is
 * GENERATED from regmap.yaml - the HAL cannot drift from the RTL
 * without the CI regmap gate failing first.
 *
 * Everything is static inline over volatile accesses: no libc, no
 * startup dependencies, usable from the mask-ROM firmware, from a
 * loaded SRAM application, and from bare test programs alike. */
#ifndef ZIRH_HAL_H
#define ZIRH_HAL_H

#include <stdint.h>
#include "../zirh_regs.h"

#define ZREG(a) (*(volatile uint32_t *)(a))

/* --- UART ---------------------------------------------------------- */
static inline int zirh_uart_tx_free(void)
{ return ZREG(UART_STATUS_ADDR) & 1u; }

static inline int zirh_uart_rx_avail(void)
{ return (ZREG(UART_STATUS_ADDR) >> 1) & 1u; }

static inline void zirh_uart_putc(uint8_t b)
{ while (!zirh_uart_tx_free()) {} ZREG(UART_TXDATA_ADDR) = b; }

static inline uint8_t zirh_uart_getc(void)
{ while (!zirh_uart_rx_avail()) {} return (uint8_t)ZREG(UART_RXDATA_ADDR); }

/* --- watchdog / liveness ------------------------------------------- */
/* Every signature write feeds the watchdog and toggles CPU_ALIVE.
 * Call once per main-loop iteration with a changing value. */
static inline void zirh_signon(uint8_t sig)
{ ZREG(HK_CPU_SIG_ADDR) = sig; }

/* --- EDAC / beam counters ------------------------------------------ */
typedef struct {
    uint16_t plain, raw_a, esc_a, raw_b, esc_b;
    uint8_t  ecc_corr, ecc_uncorr, bus_to, ferr, boots;
} zirh_counters_t;

static inline void zirh_read_counters(zirh_counters_t *c)
{
    c->plain      = (uint16_t)ZREG(HK_CNT_PLAIN_ADDR);
    c->raw_a      = (uint16_t)ZREG(HK_CNT_RAW_A_ADDR);
    c->esc_a      = (uint16_t)ZREG(HK_CNT_ESC_A_ADDR);
    c->raw_b      = (uint16_t)ZREG(HK_CNT_RAW_B_ADDR);
    c->esc_b      = (uint16_t)ZREG(HK_CNT_ESC_B_ADDR);
    c->ecc_corr   = (uint8_t)ZREG(HK_CNT_ECC_C_ADDR);
    c->ecc_uncorr = (uint8_t)ZREG(HK_CNT_ECC_U_ADDR);
    c->bus_to     = (uint8_t)ZREG(HK_CNT_BUSTO_ADDR);
    c->ferr       = (uint8_t)ZREG(HK_CNT_FERR_ADDR);
    c->boots      = (uint8_t)ZREG(HK_BOOT_CNT_ADDR);
}

static inline void zirh_counters_clear(void)
{ ZREG(HK_CTRL_ADDR) = ZREG(HK_CTRL_ADDR) | (1u << 8); }

/* one-shot fault injection (see regmap INJECT.TARGET enum) */
static inline void zirh_inject(uint8_t target)
{ ZREG(HK_INJECT_ADDR) = target; }

/* --- environment instruments --------------------------------------- */
static inline void zirh_tid_start(void)  { ZREG(HK_ENV_RO_ADDR) = 1u; }
static inline int  zirh_tid_busy(void)
{ return (ZREG(HK_ENV_RO_ADDR) >> 31) & 1u; }
static inline uint16_t zirh_tid_count(void)
{ return (uint16_t)ZREG(HK_ENV_RO_ADDR); }

static inline void zirh_set_selftest(void) { ZREG(HK_ENV_SB_ADDR) = 1u; }
static inline uint8_t zirh_set_count(void)
{ return (uint8_t)ZREG(HK_ENV_SB_ADDR); }
static inline uint8_t zirh_burst_count(void)
{ return (uint8_t)(ZREG(HK_ENV_SB_ADDR) >> 8); }

/* --- interface experiments ----------------------------------------- */
static inline void zirh_can_beacon(void) { ZREG(IFC_CAN_CTRL_ADDR) = 1u; }
static inline uint32_t zirh_can_status(void)
{ return ZREG(IFC_CAN_STAT_ADDR); }

static inline void zirh_spw_link(int en)
{ ZREG(IFC_SPW_CTRL_ADDR) = en ? 1u : 0u; }
static inline void zirh_spw_send(uint8_t ch)
{ ZREG(IFC_SPW_CTRL_ADDR) = ((uint32_t)ch << 8) | 3u; }
static inline uint32_t zirh_spw_status(void)
{ return ZREG(IFC_SPW_STAT_ADDR); }

#endif /* ZIRH_HAL_H */
