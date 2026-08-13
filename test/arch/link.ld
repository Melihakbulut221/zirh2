OUTPUT_ARCH("riscv")
ENTRY(rvtest_entry_point)
SECTIONS
{
  . = 0x00000000;
  .text.init : { *(.text.init) }
  . = ALIGN(4);
  .text : { *(.text) }
  . = ALIGN(4);
  .data : { *(.data) *(.data.*) *(.rodata) *(.rodata.*) *(.sdata*) }
  . = ALIGN(4);
  .tohost : { *(.tohost) }
  . = ALIGN(4);
  .bss : { *(.bss) *(.bss.*) *(.sbss*) }
  _end = .;
}
