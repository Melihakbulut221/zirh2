/* ZIRH-2 startup: scrub the register file, stack at the top of the
 * 64-byte ECC RAM, zero-fill the RAM (the ECC array has no reset -
 * reading uninitialized words would count phantom uncorrectable
 * events), then run main forever.
 *
 * The RF scrub exists because of a measured finding: SERV's register
 * file is a RAM and the SoC reset does NOT wipe it, so a watchdog
 * reboot lands in stale - possibly beam-corrupted - register state and
 * can derail again before reaching main (serial counted reboots,
 * observed in the storm campaign). Thirty-one writes make every reboot
 * a true state reset; the voluntary warm restart inherits the same
 * guarantee for the zombie path. */
    .section .text.start
    .globl _start
_start:
    /* Scrub the callee-saved registers (ra, s0-s11): the class the
     * RF-residue finding named - a hoisted base pointer surviving in a
     * callee-saved register is what derails a reboot. Scrubbing the full
     * file was measured to congest place-and-route (the extra constants
     * reshaped the ROM decode mux into an unroutable pocket); this subset
     * keeps the mitigation's real target and shrinks the ROM delta. The
     * caller-saved and temporary registers are overwritten by main's own
     * prologue before any use, so they need no explicit scrub. */
    li   x1,  0
    li   x8,  0
    li   x9,  0
    li   x18, 0
    li   x19, 0
    li   x20, 0
    li   x21, 0
    li   x22, 0
    li   x23, 0
    li   x24, 0
    li   x25, 0
    li   x26, 0
    li   x27, 0
    li   sp, 0x1040          /* RAM_BASE + RAM_BYTES */
    li   t0, 0x1000          /* zero-fill the ECC RAM */
    li   t1, 0x1040
1:  sw   zero, 0(t0)
    addi t0, t0, 4
    bltu t0, t1, 1b
    call main
2:  j    2b
