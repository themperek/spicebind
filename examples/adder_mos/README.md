## A four-bit CMOS adder and Verilog testbench,
derived from Ngspice's adder_mos.cir example circuit.


## To compile the testbench:
```
iverilog -o tb.vvp tb.v
```

## Run the simulation - this takes several seconds:

```
./run
```

## Plot results:
```
ngspice plot.sp
```

## Tidy up:
```
./clean
```