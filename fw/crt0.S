/* ZIRH-2 startup: stack at the top of the 64-byte ECC RAM, zero-fill the
 * RAM (the ECC array has no reset - reading uninitialized words would count
 * phantom uncorrectable events), then run main forever. */
    .section .text.start
    .globl _start
_start:
    li   sp, 0x1040          /* RAM_BASE + RAM_BYTES */
    li   t0, 0x1000          /* zero-fill the ECC RAM */
    li   t1, 0x1040
1:  sw   zero, 0(t0)
    addi t0, t0, 4
    bltu t0, t1, 1b
    call main
2:  j    2b
