# Makefile ─ simple run for tb_flash_adc8_sine

SRC           := flash_adc8.v flash_adc8_tb.v
SRC_SPICE     := flash_adc8.cir
HDL_INSTANCE  := flash_adc8_tb.dut
SPICEBIND_DIR := $(shell spicebind-vpi-path)

OUT      := flash_adc8_tb.vvp

# --------------------------------------------------------------------
# Default target: compile & run
all: $(OUT)
	SPICE_NETLIST=$(SRC_SPICE) HDL_INSTANCE=$(HDL_INSTANCE) vvp -M $(SPICEBIND_DIR) -m spicebind_vpi $(OUT)

# Compile step
$(OUT): $(SRC)
	iverilog -g2005-sv -o $@ $(SRC)

# Clean up
clean:
	rm -f $(OUT) *.raw *.vcd

.PHONY: all wave clean
