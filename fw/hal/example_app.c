/* ZIRH HAL example: the canonical flight-shaped main loop - sign on,
 * watch the counters, answer the ground. Compiles against the HAL
 * with no libc; the CI gate proves HAL and register map agree with
 * the compiler about every access. */
#include "zirh_hal.h"

void app_main(void)
{
    uint8_t sig = 1;
    zirh_counters_t c;

    zirh_counters_clear();
    zirh_spw_link(1);

    for (;;) {
        zirh_signon(sig);
        sig = (uint8_t)(sig * 5u + 1u);

        zirh_read_counters(&c);
        if (c.ecc_uncorr) {
            /* uncorrectable seen: make it loud, never hide it */
            zirh_uart_putc('U');
        }
        if (zirh_uart_rx_avail()) {
            uint8_t b = zirh_uart_getc();
            zirh_uart_putc((uint8_t)(b + 1u));   /* the echo contract */
        }
    }
}
