# SpiceBind

[![Tests](https://github.com/themperek/spicebind/actions/workflows/tests.yml/badge.svg)](https://github.com/themperek/spicebind/actions/workflows/tests.yml)
[![Docs](https://github.com/themperek/spicebind/actions/workflows/docs.yml/badge.svg)](https://themperek.github.io/spicebind/)

SpiceBind is a lightweight bridge that enables co-simulation of **analog [ngspice](https://ngspice.sourceforge.io/)** circuits alongside **HDL simulators**. This tool allows design engineers to seamlessly integrate SPICE-accurate analog models into their existing digital verification flows.

### Key Benefits

- **Preserve Your Existing Flow**: Keep your RTL, testbenches, and waveform viewers unchanged
- **SPICE Accuracy**: Replace any module with a SPICE-based analog model for accurate analog simulation
- **Unified Timeline**: Analog and digital domains run in synchronization
- **Zero Vendor Lock-in**: Works with open-source tools like Icarus Verilog up to commercial simulators (to be tested)
- **Verification Ready**: Compatible with [cocotb](https://www.cocotb.org/) for Python-based verification

### Use Cases

Perfect for ASIC designers working on:
- Mixed-signal SoCs with analog IP blocks
- ADCs, DACs, and data converters
- PLLs, oscillators, and clock generation circuits
- Power management units
- Sensor interfaces and analog front-ends

⚠️ **Note**: This is an early release. We welcome feedback and contributions from the community.

## Installation

### Prerequisites

- C++ compiler with C++17 support
- ngspice library and development headers
- Verilog VPI compatible simulator (tested with [Icarus Verilog](https://github.com/steveicarus/iverilog))
- Python 3.6+ (optional)

### Build Instructions

Clone the repository:
```bash
git clone https://github.com/themperek/spicebind.git
cd spicebind
```

**Option 1: Standalone VPI Module**
```bash
mkdir build && cd build
cmake ..
cmake --build .
cmake --build . --target debug  # Optional: builds debug version
```

**Option 2: Python Integration**
```bash
pip install -e .
```

## Quick Start

### 1. Define Your Analog Block

Create a Verilog module with matching SPICE netlist with external voltage sources and ouptut ports.

**Verilog module** (e.g., `adc.v`):
```verilog
module adc(
    input  real vin,
    output reg [3:0] code
);
endmodule
```

**SPICE netlist** (e.g., `adc.cir`):
```spice
* External voltage source for input
Vvin adc_in 0 0 external

* ADC subcircuit instantiation
Xadc adc_in code[3] code[2] code[1] code[0] sar_adc

* Simulation settings
.tran 1ns 1
```

### 2. Configure Environment

Set the required environment variables:
```bash
export SPICE_NETLIST=adc.cir
export HDL_INSTANCE=tb.adc
export VCC=3.3
```

### 3. Run Simulation

For Icarus Verilog:
```bash
vvp -M $(spicebind-vpi-path) -m spicebind_vpi tb.vvp
```

See the `examples/` directory for complete working examples.

### Multiple Instance Support

For designs with multiple analog blocks, configure each instance in your SPICE netlist with full hierarchical paths:

**SPICE netlist**:
```spice
* First ADC instance
Vtb.adc.vin vin 0 0 external
Xadc vin tb.adc.code[3] tb.adc.code[2] tb.adc.code[1] tb.adc.code[0] sar_adc

* Inverter instance
Vtb.inv.A inv_a 0 0 external
Xinv inv_a tb.inv.Y inv

.tran 1ns 1
```

**Environment configuration**:
```bash
export HDL_INSTANCE=tb.adc,tb.inv
```

### Configuration Options

- `SPICE_NETLIST`: Path to your SPICE netlist file
- `HDL_INSTANCE`: Comma-separated list of HDL instance paths
- `VCC`: Supply voltage for analog simulation
- Additional options available in the documentation

## Documentation

For detailed documentation, examples, and API reference, visit: [https://themperek.github.io/spicebind/](https://themperek.github.io/spicebind/)

## Contributing

We welcome contributions! Please see our contributing guidelines and feel free to:
- Report bugs and request features via GitHub Issues
- Submit pull requests for improvements
- Share your use cases and examples

## Roadmap

- [ ] Enhanced testing and validation
- [ ] Bidirectional bus support
- [ ] Automatic SPICE wrapper generation
