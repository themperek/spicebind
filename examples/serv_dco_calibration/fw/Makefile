# Minimal RV32I firmware. Invoked by tools/regenerate.py inside
# IIC-OSIC-TOOLS (https://github.com/iic-jku/IIC-OSIC-TOOLS)
# or with a local RISC-V GCC via RISCV_PREFIX.

PREFIX  ?= riscv64-unknown-elf-
CC      := $(PREFIX)gcc
OBJCOPY := $(PREFIX)objcopy
OBJDUMP := $(PREFIX)objdump

CFLAGS := -march=rv32i -mabi=ilp32 -Os -ffreestanding -nostdlib -nostartfiles \
          -Wall -Wextra -fno-builtin -mno-relax
LDFLAGS := -T link.ld -nostdlib -nostartfiles -mno-relax

OUT ?= $(abspath ../generated)
ELF := $(OUT)/firmware.elf
HEX := $(OUT)/firmware.hex
LST := $(OUT)/firmware.lst

.PHONY: all clean
all: $(LST) $(HEX)

$(OUT):
	mkdir -p $(OUT)

$(ELF): start.S calibrate.c link.ld | $(OUT)
	$(CC) $(CFLAGS) $(LDFLAGS) start.S calibrate.c -o $@

$(LST): $(ELF)
	cd $(OUT) && printf '%s\n' '; Generated. Do not edit.' > $(notdir $(LST)) && $(OBJDUMP) -d -M numeric,no-aliases $(notdir $(ELF)) >> $(notdir $(LST))

$(HEX): $(ELF) $(LST)
	$(OBJCOPY) -O binary $< $(OUT)/firmware.bin
	python3 ../tools/bin2hex.py $(OUT)/firmware.bin $@
	rm -f $(OUT)/firmware.bin $(ELF)

clean:
	rm -f $(OUT)/firmware.elf $(OUT)/firmware.bin $(OUT)/firmware.hex $(OUT)/firmware.lst
