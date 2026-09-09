`timescale 1ns/1ps

module test_cir(
    input real vin,
    output wire y
);
endmodule

module tb;
    real vin;
    wire y;

    test_cir test_cir (
        .vin(vin),
        .y(y)
    );

    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0);
    end
endmodule
