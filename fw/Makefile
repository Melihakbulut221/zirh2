# ZIRH-2 firmware: rv32i, built with the standard Ubuntu RISC-V toolchain.
# CI runs this (see .github/workflows/fw.yaml); the resulting rom.hex is
# committed so the RTL flow never depends on having a toolchain installed.

CROSS   ?= riscv64-unknown-elf-
CFLAGS  = -march=rv32i -mabi=ilp32 -Os -Wall -Wextra -ffreestanding \
          -nostdlib -fno-builtin
BUILD   = build

all: $(BUILD)/rom.hex

$(BUILD)/fw.elf: crt0.S main.c zirh.h link.ld | $(BUILD)
	$(CROSS)gcc $(CFLAGS) -T link.ld -o $@ crt0.S main.c
	$(CROSS)size $@

$(BUILD)/fw.bin: $(BUILD)/fw.elf
	$(CROSS)objcopy -O binary $< $@

$(BUILD)/rom.hex: $(BUILD)/fw.bin
	python3 rom_gen.py $< $@ ../src/rom_init.vh
	$(CROSS)objdump -d $(BUILD)/fw.elf > $(BUILD)/fw.disasm

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)

.PHONY: all clean
