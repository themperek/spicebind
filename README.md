# SpiceBind

⚠️ **Warning**: This is a very early proof of concept.

SpiceBind is a lightweight bridge that lets you co-simulate **true-transistor [ngspice](https://ngspice.sourceforge.io/)** circuits alongside **HDL simulators**. You keep your existing RTL, testbench, and waveform viewer, but analog blocks now run at SPICE accuracy inside the same timeline. Mixed-signal simulation with zero vendor lock-in—from Icarus Verilog all the way to commercial tools. You can even use [cocotb](https://www.cocotb.org/) on top for verification.

## Installation

### Prerequisites

- A g++ compiler with C++17 support
- The ngspice library and development headers
- A Verilog simulator (only tested with Icarus)
- Python (optional)

### Install

Clone repository:

```cmd
git clone https://github.com/themperek/spicebind.git
cd spicebind
```

For standalone spicebind_vpi module in `spicebind` folder:

```
mkdir build && cd build
cmake ..
cmake --build . 
cmake --build . --target debug       # builds the debug
```

With python:

```cmd
pip install -e .
```

## Usage

Your SPICE netlist ports have to match empty Verilog module ports. Inputs need to be defined as external voltage sources.
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

In order to enable mixed-signal mode, you need to at minimum define `SPICE_NETLIST` and `HDL_INSTANCE` environmental variables:
```cmd
export SPICE_NETLIST=adc.cir 
export HDL_INSTANCE=tb.adc
``` 

and load VPI module. For Icarus:
```cmd
vvp -M $(spicebind-vpi-path) -m spicebind_vpi tb.vvp
```

See `examples` folder for more.

## Roadmap

- Testing 
- Examples
- Configuration file
- Multiple instance support
