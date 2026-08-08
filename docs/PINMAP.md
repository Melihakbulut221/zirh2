# ZIRH-2 pin map (REV 2, 2026-08-08; rev 1 frozen 2026-08-07)

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
| uio[0] | CAN_RX | in | CAN bus level, 1 = recessive; bench loopback from CAN_TX |
| uio[1] | CAN_TX | out | wired-AND CAN drive: beacons plus the receiver's ACK pull |
| uio[2] | SPW_DIN | in | SpaceWire data in |
| uio[3] | SPW_SIN | in | SpaceWire strobe in |
| uio[4] | SPW_DOUT | out | SpaceWire data out |
| uio[5] | SPW_SOUT | out | SpaceWire strobe out |
| uio[6] | - | in | unused |
| uio[7] | - | in | unused |

Unused ui pins are deliberately NOT given functions: every input pin is
an SET path into the die, and the CPU-era chip does not need them.

REV 2 (2026-08-08): the uio bank, reserved for ZIRH-3 in rev 1, now
carries the two interface experiments pulled forward from the P1/P2
scope - CAN 2.0A-lite (2 pins, exactly the budget the scope recorded)
and SpaceWire-lite (4 pins: single-ended Data-Strobe both directions;
the standard's LVDS pairs are not a thing TT pads can do, which is one
reason it is -lite). Both are loopback bench links: CAN_TX to CAN_RX
with one wire, SPW_DOUT/SOUT to SPW_DIN/SIN with two. All counters and
state read over the UART command path ('k'/'K'/'w'/'W'); the telemetry
frame is unchanged. ui bank and all uo pins: untouched from rev 1, so
the one-cable ZIRH-1 bench compatibility stands.
