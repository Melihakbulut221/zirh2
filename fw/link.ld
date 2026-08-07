/* ZIRH-2: 1 KB mask ROM at 0, 64 B ECC RAM at 0x1000. */
MEMORY
{
    ROM (rx)  : ORIGIN = 0x00000000, LENGTH = 1K
    RAM (rw)  : ORIGIN = 0x00001000, LENGTH = 64
}
SECTIONS
{
    .text : { *(.text.start) *(.text*) *(.rodata*) } > ROM
    /DISCARD/ : { *(.eh_frame) *(.comment) *(.riscv.attributes) }
}
