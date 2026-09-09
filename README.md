
<center><img src="docs/assets/spicebind_logo.svg" alt="SpiceBind" height="60">

[![Tests](https://github.com/themperek/spicebind/actions/workflows/tests.yml/badge.svg)](https://github.com/themperek/spicebind/actions/workflows/tests.yml)
[![Documentation](https://github.com/themperek/spicebind/actions/workflows/docs.yml/badge.svg)](https://themperek.github.io/spicebind/)
[![PyPI](https://img.shields.io/pypi/v/spicebind.svg)](https://pypi.org/project/spicebind/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](https://github.com/themperek/spicebind/blob/main/LICENSE)

</center>

**Run SPICE circuits as blocks inside your existing Verilog simulation.**

SpiceBind embeds [ngspice](https://ngspice.sourceforge.io/) into a VPI-capable HDL simulator. Replace only the blocks that need circuit-level simulation. RTL, testbench, cocotb, and the digital verification flow stay in the HDL simulator.

It is useful for mixed-signal simulation in general, and especially when the digital part is large.

> SpiceBind is an early project. It is tested with Icarus Verilog, Verilator, and ngspice. The plugin uses VPI, so it is not tied to those two HDL simulators, but others have not been qualified.

![SPI ADC mixed-signal simulation in Surfer](docs/assets/spi_adc_surfer.png)


The `spi_adc` example above crosses the HDL/SPICE boundary in both directions. `vin` is passed from HDL into ngspice, the ADC code is calculated by the SPICE model, and HDL logic shifts the result out over SPI.

## What it does

- RTL, testbenches, cocotb, and digital simulation stay in the HDL simulator you already use. You do not have to move the design into a mixed-signal environment.
- The plugin uses standard VPI, so it can attach to open-source or commercial HDL simulators. It is tested with Icarus Verilog and Verilator. Other VPI-capable simulators still need qualification. You can change the simulator without changing the RTL, testbench, or how SpiceBind maps instances.
- Selected HDL instances can be backed by transistor-level or analog SPICE models. The rest of the design stays RTL.
- HDL events stay in lock-step with ngspice adaptive timesteps, including events that fall inside an analog step.

## Why HDL-first?

A mixed-signal design is often mostly RTL with a few analog blocks. Putting the whole system under SPICE can mean rewriting the testbench and how the digital part is simulated.


## Architecture

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'lineColor': '#22808f',
    'textColor': '#1c3d42',
    'fontSize': '14px'
  }
}}%%

flowchart LR

    TB["Testbench / cocotb\n{test.v} / {test.py}"]:::tb

    subgraph DUT["Design Under Test\n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{dut.v}"]
        direction LR

        ADC["ADC (stub)\n{adc.v}"]:::hdl
        FE["Sensor (stub)\n{sensor.v}"]:::hdl

        DD["\n\nDigital Design\n{core.v}\n\n\n"]:::hdl

        DD <--> ADC
        DD <--> FE
    end

    SB["SpiceBind<br/>time synchronization<br/>D/A + A/D"]:::bridge

    subgraph NG["ngspice"]
        direction LR
        ADCSP["ADC (SPICE)\n{adc.cir}"]:::analog
        FESP["Sensor (SPICE)\n{sensor.cir}"]:::analog
    end

    TB <--> DUT
    DUT <-->|VPI| SB
    SB <-->|libngspice| NG

    %% Custom Class Definitions based on SVG Palette
    classDef hdl fill:#eef7f8,stroke:#22808f,stroke-width:2.5px,color:#1c3d42,font-weight:bold;
    classDef analog fill:#fff5eb,stroke:#d9772b,stroke-width:2.5px,color:#b8540a,font-weight:bold;
    classDef bridge fill:#e07a2d,stroke:#e07a2d,color:#ffffff,stroke-width:2px,font-weight:bold;
    classDef tb fill:#fcfbb4,stroke:#d1ce00,stroke-width:2.5px,color:#1c3d42,font-weight:bold;

    %% Subgraph Styles
    style DUT fill:#ffffff,stroke:#22808f,stroke-width:2.5px,color:#22808f
    style NG fill:#ffffff,stroke:#d9772b,stroke-width:2.5px,color:#d9772b
    style DD fill:#ffffff,stroke:#22808f,stroke-width:2.5px,color:#22808f
```

The HDL side sees a normal module instance. The module body can be empty. SpiceBind finds the selected instance through VPI and connects its ports to sources and nodes in the SPICE circuit.

Digital-to-analog values go to ngspice through external voltage sources. Analog results are read back and driven onto the corresponding HDL outputs.

The two simulators have independent event and timestep mechanisms, so exchanging values is not enough. SpiceBind also keeps simulation time in lock-step. VPI callbacks detect HDL events, ngspice callbacks report analog progress, and a time barrier stops either engine from running ahead. If an HDL event lands inside an ngspice step, ngspice repeats that step at the event time.

See the [timing synchronization documentation](https://themperek.github.io/spicebind/).

## Quick start

### Requirements

- C++17 compiler (needed to build the VPI plugin)
- ngspice shared library and development headers
- Verilog VPI compatible simulator (tested with [Icarus Verilog](https://github.com/steveicarus/iverilog) and [Verilator](https://www.veripool.org/verilator/) 5)
- Python 3.10+

On Debian/Ubuntu:

```bash
sudo apt install build-essential cmake iverilog ngspice libngspice0-dev python3-venv
```

Icarus Verilog from that package set is enough to run the examples. Verilator needs a recent 5.x build with `--timing` and `--vpi` (CI compiles it from git; distro packages are often too old).

Install the released package:

```bash
pip install spicebind
```

If ngspice is not on `PATH`, point CMake at its install prefix (`include/` and `lib/`):

```bash
NGSPICE_ROOT=/path/to/ngspice pip install spicebind
```

Run the SPI ADC example (Icarus Verilog by default; `SIM=verilator` selects Verilator):

```bash
python examples/spi_adc/test_spi_adc.py
SIM=verilator python examples/spi_adc/test_spi_adc.py
```

For development:

```bash
git clone https://github.com/themperek/spicebind.git
cd spicebind
pip install -e ".[dev]"
```

Standalone VPI build (no Python package):

```bash
cmake -S . -B build  # optional: -DNGSPICE_ROOT=/path/to/ngspice
cmake --build build
cmake --build build --target debug  # Optional: debug VPI
```

## Binding an HDL instance to SPICE

The HDL contains a module with the interface that the rest of the design expects:

```verilog
module adc_core(
    input  real      vin,
    output     [7:0] code,
    input             range0,
    input             range1
);
    // implemented in SPICE
endmodule
```

The corresponding SPICE netlist provides external sources for HDL inputs and nodes for HDL outputs:

```spice
Vvin    vin    0 0 external
Vrange0 range0 0 0 external
Vrange1 range1 0 0 external

* Analog implementation
Xadc vin ref vcc code[7] code[6] code[5] code[4] code[3] code[2] code[1] code[0] adc_ideal_8bit

.tran 1ns 100us
.end
```

At runtime, select the netlist and HDL instance:

```bash
export SPICE_NETLIST=examples/spi_adc/spi_adc.cir
export HDL_INSTANCE=spi_adc.adc_inst
export VCC=3.3
```

The VPI module can then be loaded by the HDL simulator.

Icarus Verilog:

```bash
vvp -M "$(spicebind-vpi-path)" -m spicebind_vpi simulation.vvp
```

Verilator (`--vpi --timing`); pass the plugin as a plusarg:

```bash
./Vtop +verilator+vpi+"$(spicebind-vpi-path)/spicebind_vpi.vpi"
```

The examples use the cocotb runner or small shell scripts to set this up automatically. `$SIM` selects the HDL simulator (`icarus` default, or `verilator`). The full suite is `nox -s test` (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Runtime configuration

| Variable | Meaning |
| --- | --- |
| `SPICE_NETLIST` | Path to the ngspice netlist |
| `HDL_INSTANCE` | HDL instance path, or a comma-separated list of instance paths |
| `VCC` | Voltage used for digital-to-analog conversion. Default: `1.0` |
| `SPICE_DUMP_RAW` | Write ngspice transient data to `dump.raw` at shutdown |

## Examples

| Example | What it shows |
| --- | --- |
| [`examples/adc`](https://github.com/themperek/spicebind/tree/main/examples/adc) | 8-bit ADC with Verilog and cocotb testbenches |
| [`examples/adder_mos`](https://github.com/themperek/spicebind/tree/main/examples/adder_mos) | Four-bit CMOS adder derived from the ngspice MOS adder example |
| [`examples/spi_adc`](https://github.com/themperek/spicebind/tree/main/examples/spi_adc) | HDL SPI interface connected to an ADC implemented in SPICE |
| [`examples/serv_dco_calibration`](https://github.com/themperek/spicebind/tree/main/examples/serv_dco_calibration) | SERV firmware calibrates a transistor-level DCO through SpiceBind |

## How this differs from other open-source flows

There are several ways to combine HDL and SPICE. They differ mainly in which simulator owns the top level and how the digital part is executed.

| Approach | Top-level environment | Digital execution | Analog engine | What it does |
| --- | --- | --- | --- | --- |
| SpiceBind | HDL simulator | Normal HDL simulation | ngspice shared library | Selected HDL instances are replaced by SPICE while the HDL flow stays in place |
| ngspice `d_cosim` | ngspice / XSPICE | HDL compiled with Verilator, Icarus Verilog, or GHDL and loaded as an XSPICE model | ngspice | SPICE-first flow with HDL blocks inside the ngspice netlist |
| Yosys to XSPICE | ngspice / XSPICE | Synthesizable RTL mapped to XSPICE gates and storage elements | ngspice | One simulator at runtime, but the RTL is reduced to synthesized logic |
| [`cocotbext-ams`](https://github.com/VLSIDA/cocotbext-ams) | cocotb / Python | Normal HDL simulator through cocotb | ngspice or Xyce | Python coordinates the HDL and analog simulators |

A SPICE-first flow fits when the analog netlist is already the top level. Synthesizing RTL into XSPICE avoids synchronizing two simulators at runtime. SpiceBind is for the other case: a digital simulation already exists and only selected blocks need SPICE.

Commercial Verilog-AMS and real-number-modeling flows are not compared here.

## Current scope

SpiceBind currently focuses on:

- ngspice as the analog engine
- Verilog through VPI
- Icarus Verilog and Verilator as the tested HDL simulators
- binding selected HDL instances to SPICE
- event and timestep synchronization between HDL and ngspice
- cocotb compatibility, without requiring cocotb

The VPI plugin is not tied to those two HDL simulators, but others have not been tested.

## Documentation

Tutorials, configuration, API notes, and timing:

https://themperek.github.io/spicebind/

## Talks

[OrConf 2026](https://fossi-foundation.org/orconf/2026#spicebind-bringing-spice-into-rtl-verification): *SpiceBind: Bringing SPICE into RTL Verification*. [Slides](https://themperek.github.io/spicebind/orconf_2026.html) ([PDF](https://themperek.github.io/spicebind/talks/orconf-2026/SpiceBind-OrConf-2026.pdf)).

## Contributing

Bug reports, examples, and pull requests are welcome. Use the [GitHub issue tracker](https://github.com/themperek/spicebind/issues) for bugs, questions, and feature proposals.

## License

SpiceBind is distributed under the BSD 3-Clause License. See [LICENSE](https://github.com/themperek/spicebind/blob/main/LICENSE).

## Development note

SpiceBind is developed with assistance from generative AI tools.
All generated or modified code is reviewed, tested, and maintained
like any other contribution.