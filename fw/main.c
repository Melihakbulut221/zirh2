/* ZIRH-2 housekeeping firmware v2.
 *
 * The ground command set, one byte per command (anything else echoes
 * back incremented, which keeps the firmware path distinguishable from
 * ZIRH-1's hardware echo):
 *
 *   '0'..'4'  inject: plain / one A-replica / all-A (escape) /
 *             one B-replica / all-B  -> exactly +1 on the right counter
 *             in the next telemetry frame
 *   'a'/'b'/'c'  pattern mode: zeros / ones / checkerboard
 *   'C'       clear all counters (mode preserved)
 *   'R'       reply with the ROM checksum byte (XOR of all 256 words,
 *             folded) - computed at boot through the ROM's data port,
 *             so a corrupted mask answers wrong or not at all
 *
 * The rolling liveness signature is written to the housekeeping block
 * every loop iteration: telemetry carries it, and the hardware watchdog
 * reboots the SoC if it ever stops arriving.
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

static uint8_t rom_checksum(void)
{
    const volatile uint32_t *rom = (const volatile uint32_t *)0x00000000u;
    uint32_t x = 0;
    for (uint32_t i = 0; i < 256u; i++)
        x ^= rom[i];
    x ^= x >> 16;
    x ^= x >> 8;
    return (uint8_t)x;
}

int main(void)
{
    uint32_t count = 0;
    uint32_t sig = 0x5A5A5A5Au;
    uint8_t rom_sum = rom_checksum();

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
            if (b >= '0' && b <= '4')
                HK_INJECT = (uint32_t)(b - '0');
            else if (b >= 'a' && b <= 'c')
                HK_CTRL = (uint32_t)(b - 'a');
            else if (b == 'C')
                HK_CTRL = 0x100u | (HK_CTRL & 3u);
            else if (b == 'R')
                tx_byte(rom_sum);
            else
                tx_byte((uint8_t)(b + 1u));
        }
    }
}
