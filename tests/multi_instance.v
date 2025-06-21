`timescale 1ns/1ps

module inv(input wire A, output wire Y);

endmodule

module tb(
    input wire A0, A1,
    output wire Y0, Y1
);

    inv inv0 (.A(A0), .Y(Y0));
    inv inv1 (.A(A1), .Y(Y1));

    initial begin
        $dumpfile("multi_instance.vcd");
        $dumpvars (0);
    end

endmodule
