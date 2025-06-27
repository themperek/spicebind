`timescale 1ns/1ps

module debug(
    input wire A0, A1, A2,
    output wire Y0, Y1, Y2
);

endmodule

module tb(
    input wire A0, A1, A2,
    output wire Y0, Y1, Y2
);

   debug debug (.A0(A0), .A1(A1), .A2(A2), .Y0(Y0), .Y1(Y1), .Y2(Y2));

    initial begin
        $dumpfile("debug.vcd");
        $dumpvars (0);
    end

endmodule
