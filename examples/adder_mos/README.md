## A four-bit CMOS adder and Verilog testbench,
derived from Ngspice's adder_mos.cir example circuit.


## To compile the testbench (Icarus Verilog):
```
iverilog -o tb.vvp tb.v
```

## Run the simulation - this takes several seconds:

```
./run
```

## Verilator 5 (experimental)

SpiceBind's VPI plugin can also be loaded by Verilator (`--vpi --timing`).

```
./run_verilator
```

Needs Verilator 5.x with `--timing` and `--vpi`. The same `tb.v` and netlist as Icarus.

## Plot results:
```
ngspice plot.sp
```

## Tidy up:
```
./clean
```