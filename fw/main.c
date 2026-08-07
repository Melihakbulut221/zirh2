/* ZIRH-2 housekeeping firmware v1.
 *
 * Scope matches the hardware that exists on the zirh2-p0 branch: ROM, ECC
 * RAM, UART registers over the bus. Until the SEU monitor grows its bus
 * wrapper, the loop proves three things end to end: the CPU executes from
 * mask ROM, the ECC RAM carries live state, and the command link works.
 *
 *   - beacon: every 2^16 loop iterations, send 'Z' followed by a rolling
 *     liveness signature byte (XOR-rotate over the loop counter). A stuck
 *     or corrupted CPU stops producing valid signatures - visible from the
 *     ground without any polling.
 *   - echo+1: every received byte is answered with byte+1, which proves RX,
 *     TX and the firmware path in one exchange (plain echo would be
 *     indistinguishable from the hardware echo of ZIRH-1).
 */
#include "zirh.h"

static uint32_t sig_step(uint32_t s)
{
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    return s ? s : 1u;
}

static void tx_byte(uint8_t b)
{
    while (!(UART_STATUS & UART_TX_FREE))
        ;
    UART_TXDATA = b;
}

int main(void)
{
    uint32_t count = 0;
    uint32_t sig = 0x5A5A5A5Au;

    /* live state parked in ECC RAM so the RAM is exercised continuously */
    volatile uint32_t *loops = (volatile uint32_t *)RAM_BASE;
    volatile uint32_t *sigw  = (volatile uint32_t *)(RAM_BASE + 4);

    for (;;) {
        count++;
        *loops = count;
        sig = sig_step(sig ^ count);
        *sigw = sig;
        HK_CPU_SIG = sig & 0xFFu;   /* liveness signature into telemetry */

        if ((count & 0xFFFFu) == 0) {
            tx_byte('Z');
            tx_byte((uint8_t)(sig & 0xFFu));
        }

        if (UART_STATUS & UART_RX_AVAIL) {
            uint8_t b = (uint8_t)UART_RXDATA;
            tx_byte((uint8_t)(b + 1u));
        }
    }
}
