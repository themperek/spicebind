# SpiceBind

⚠️ **Warning**: This is a very early proof of concept.

SpiceBind is a lightweight bridge that lets you co-simulate **true-transistor ngspice** circuits alongside **VPI-capable Verilog/SystemVerilog simulator**. You keep your existing RTL, testbench, and waveform viewer, but analog blocks now run at SPICE accuracy inside the same timeline. Mixed-signal simulation with zero vendor lock-in—from Icarus Verilog all the way to commercial tools. You can even use [cocotb](https://www.cocotb.org/) on top for verification.

## Installation

### Prerequisites

- g++ compiler with C++17 support
- ngspice library and development headers
- Verilog simulator (only tested with Icarus)
- Python (optional)

### Install

Clone repository:

```cmd
git clone https://github.com/themperek/spicebind.git
cd spicebind
```

Foe standalone vpi module in `spicebind` folder:

```
mkdir build && cd build
cmake ..                   # (optionally -DNGSPICE_ROOT=/path)
cmake --build .            # builds release flavour
cmake --build . --target debug       # builds the debug
```

With python:

```cmd
pip install -e .
```

## Usage

[TODO] See `tests` folder.

## Roadmap

- Testing 
- Examples
- Configuration file
- Multi instance support
