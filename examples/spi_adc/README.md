# SPI controlled ADC example

This example demonstrates connecting a simple SPI block with an ADC modeled in SPICE.

## Running the test

Install the required Python packages:
```bash
pip install pytest cocotb cocotbext-spi
```

Execute the cocotb test (Icarus Verilog by default):
```bash
python test_spi_adc.py
```

Verilator 5:
```bash
SIM=verilator python test_spi_adc.py
```

Build products go under `sim_build/<simulator>/`.
```bash
WAVES=1 python test_spi_adc.py
```
