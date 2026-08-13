/* ZIRH loaded-application layout (docs/BOOT.md): the image executes
 * from the SECDED SRAM bank the boot controller committed. Bank A at
 * word 0 of the SRAM window; the 12-byte image header is NOT part of
 * the loaded payload (the controller strips it). */
OUTPUT_ARCH("riscv")
ENTRY(app_main)
MEMORY { BANK (rwx) : ORIGIN = 0x00004000, LENGTH = 2036 }
SECTIONS {
  .text : { *(.text.init) *(.text*) } > BANK
  .data : { *(.data*) *(.rodata*) *(.sdata*) } > BANK
  .bss  : { *(.bss*) *(.sbss*) } > BANK
}
