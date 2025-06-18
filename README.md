# SpiceBind

[![Tests](https://github.com/themperek/spicebind/actions/workflows/tests.yml/badge.svg)](https://github.com/themperek/spicebind/actions/workflows/tests.yml)
[![Docs](https://github.com/themperek/spicebind/actions/workflows/docs.yml/badge.svg)](https://themperek.github.io/spicebind/)



⚠️ **Warning**: This is a very early proof of concept.

SpiceBind is a lightweight bridge that lets you co-simulate **true-transistor [ngspice](https://ngspice.sourceforge.io/)** circuits
alongside **HDL simulators**.
You keep your existing RTL, testbench, and waveform viewer, but analog blocks now run at SPICE accuracy inside the same timeline.
Mixed-signal simulation with zero vendor lock-in — from Icarus Verilog all the way to commercial tools.
You can even use [cocotb](https://www.cocotb.org/) on top for verification.

## Installation

### Prerequisites

- A C++ compiler with C++17 support
- The ngspice library and development headers
- A Verilog VPI compatible simulator (only tested with [Icarus](https://github.com/steveicarus/iverilog) )
- Python (optional)

### Install

Clone the repository:
```
git clone https://github.com/themperek/spicebind.git
cd spicebind
```

For a standalone `spicebind_vpi` module in the `spicebind` folder:
```
mkdir build && cd build
cmake ..
cmake --build .
cmake --build . --target debug  # builds the debug version
```

With Python:
```
pip install -e .
```

## Usage

Your SPICE netlist ports have to match empty Verilog module ports.
Inputs need to be defined as external voltage sources.

Example for an ADC defined in Verilog:
```verilog
module adc(
    input  real vin,
    output reg [3:0] code
);
```

SPICE netlist needs to include:
```
Vvin vin 0 0 external
Xadc vin code[3] code[2] code[1] code[0] sar_adc
.tran 1ns 1
```

In order to enable mixed-signal mode, you need to at a minimum define the
`SPICE_NETLIST` and `HDL_INSTANCE` environment variables:
```
export SPICE_NETLIST=adc.cir
export HDL_INSTANCE=tb.adc
export VCC=3.3
```

and load the VPI module. For Icarus:
```bash
vvp -M $(spicebind-vpi-path) -m spicebind_vpi tb.vvp
```

See the `examples` folder for more.

## Roadmap

- Testing
- Examples
- Configuration file
- Multiple instance support
