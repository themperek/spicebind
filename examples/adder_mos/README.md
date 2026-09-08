## A four-bit CMOS adder and Verilog testbench,
derived from Ngspice's adder_mos.cir example circuit.

Icarus Verilog and Verilator 5 both run this example (`--vpi --timing` on Verilator). The same `tb.v` and netlist are used.

## To compile the testbench (Icarus Verilog):
```
iverilog -o tb.vvp tb.v
```

## Run the simulation - this takes several seconds:

```
./run
```

## Verilator 5

```
./run_verilator
```

Or `SIM=verilator pytest -v examples/adder_mos`.

## Plot results:
```
ngspice plot.sp
```

## Tidy up:
```
./clean
```
