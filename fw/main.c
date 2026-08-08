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
 *
 * PERIODIC VOLUNTARY RESTART: a register flip can leave a ZOMBIE - the
 * loop and signature alive, but a base pointer hoisted into a
 * callee-saved register corrupted, so one peripheral path is dead while
 * the watchdog stays fed (measured in the RF-flip campaign). Every 2^22
 * iterations (minutes at silicon rate, never reached in simulation) the
 * firmware jumps back to _start and re-derives ALL register state from
 * ROM constants, clearing any such state within a bounded window. This
 * is a warm jump, not a reset: the hardware BOOT counter only counts
 * real watchdog reboots.
 */

extern void _start(void);
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

        if ((count & 0x3FFFFFu) == 0u)
            ((void (*)(void))_start)();   /* voluntary warm restart */

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
            else if (b == 'T') {
                /* run one oscillator window; a dead env block leaves the
                   busy bit stuck and the watchdog turns that into a
                   counted reboot - intentionally no software timeout */
                HK_ENV_RO = 1u;
                while (HK_ENV_RO & ENV_RO_BUSY)
                    ;
                uint32_t r = HK_ENV_RO;
                tx_byte((uint8_t)(r >> 8));
                tx_byte((uint8_t)r);
            }
            else if (b == 'S')
                tx_byte((uint8_t)HK_ENV_SB);
            else if (b == 'B')
                tx_byte((uint8_t)(HK_ENV_SB >> 8));
            else if (b == 'E') {
                HK_ENV_SB = 1u;   /* fire a pulse down the SET chain */
                tx_byte('e');
            }
            else if (b == 'k') {
                /* one CAN beacon; payload = low loop-count byte */
                IFC_CAN_CTRL = ((count & 0xFFu) << 8) | 1u;
                tx_byte('b');
            }
            else if (b == 'K') {
                uint32_t r = IFC_CAN_STAT;
                tx_byte((uint8_t)(r >> 8));    /* rx_ok  */
                tx_byte((uint8_t)(r >> 16));   /* errors */
            }
            else if (b == 'w') {
                /* link enable + queue one 0xA5 data char */
                IFC_SPW_CTRL = (0xA5u << 8) | 3u;
                tx_byte('y');
            }
            else if (b == 'W') {
                uint32_t r = IFC_SPW_STAT;
                tx_byte((uint8_t)(r & 7u));    /* link state  */
                tx_byte((uint8_t)(r >> 24));   /* rx char     */
                tx_byte((uint8_t)(r >> 16));   /* errors      */
            }
            else
                tx_byte((uint8_t)(b + 1u));
        }
    }
}
