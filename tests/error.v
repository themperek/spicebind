`timescale 1ns/1ps

module error_cir();

endmodule

module error_tb();

    error_cir error_cir ();

    initial begin
        $dumpfile("error.vcd");
        $dumpvars (0);
    end

endmodule
