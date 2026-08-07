# ZIRH-2 pin map (FROZEN 2026-08-07)

Principle carried over from ZIRH-1: the pins that remain are the ones
that must work when the CPU does not. Everything else moved onto the
bus and travels over the UART command path.

Bench compatibility is deliberate: UART_RX, UART_TX and HEARTBEAT sit
on the same pins as ZIRH-1, so one cable and one ground-station command
serve both chips.

| Pin | Name | Dir | Function |
|---|---|---|---|
| ui[0] | - | in | unused, tie low |
| ui[1] | - | in | unused, tie low |
| ui[2] | - | in | unused, tie low |
| ui[3] | UART_RX | in | command/echo input, idles high (ZIRH-1 position) |
| ui[4] | - | in | unused, tie low |
| ui[5] | - | in | unused, tie low |
| ui[6] | - | in | unused, tie low |
| ui[7] | - | in | unused, tie low |
| uo[0] | HEARTBEAT | out | ~1.2 Hz; clk_rst alive (ZIRH-1 position) |
| uo[1] | CPU_ALIVE | out | toggles per firmware signature write; frozen pin + blinking HEARTBEAT = computer dead, instrument alive |
| uo[2] | SEU_EVT | out | any monitor ring event (scope the beam) |
| uo[3] | ERR_TMR | out | any TMR replica mismatch on the die |
| uo[4] | UART_TX | out | telemetry v2 + firmware responses (ZIRH-1 position) |
| uo[5] | ECC_EVT | out | ECC RAM corrected or uncorrected event |
| uo[6] | BUS_TIMEOUT | out | bus watchdog fired |
| uo[7] | ARMED | out | monitor warm-up complete |
| uio[7:0] | - | in | unused, held as inputs (reserved for ZIRH-3) |

Unused ui pins are deliberately NOT given functions: every input pin is
an SET path into the die, and the CPU-era chip does not need them. The
uio bank stays input-only (no RD_DATA bus as on ZIRH-1 - counter
readout goes over telemetry and the bus).
