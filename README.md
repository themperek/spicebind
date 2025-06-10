# SpiceBind

⚠️ **Warning**: This is a very early proof of concept.

SpiceBind is a lightweight bridge that lets you co-simulate **true-transistor ngspice** circuits alongside **VPI-capable Verilog/SystemVerilog simulator**. You keep your existing RTL, testbench, and waveform viewer, but analog blocks now run at SPICE accuracy inside the same timeline. Mixed-signal simulation with zero vendor lock-in—from Icarus Verilog all the way to commercial tools. You can even use [cocotb](https://www.cocotb.org/) on top for verification.

## Installation

### Prerequisites

- Python
- g++ compiler with C++17 support
- ngspice library and development headers
- Verilog simulator (only tested with Icarus)

### Install

```cmd
git clone https://github.com/themperek/spicebind.git
cd spicebind
pip install -e .
```

## Usage

[TODO] See `tests` folder.

## Roadmap

- Testing 
- Examples
- Configuration file
- Multi instance support
