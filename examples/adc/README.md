# Simple ADC example


## For a simple Verilog-only testbench
```
make
```

## For a cocotb-based testbench

Install dependencies:
```
pip install pytest cocotb numpy matplotlib
```

Run test. Icarus Verilog is the default; Verilator is also supported:
```
python test_flash_adc8.py
```

Verilator 5:
```
SIM=verilator python test_flash_adc8.py
```

Build products go under `sim_build/<simulator>/`.
