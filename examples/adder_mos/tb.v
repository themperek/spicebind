/* Testbench for 4-bit adder made with spicebind. */

`timescale 1ns / 1ns

module adder(a, b, y);
   input wire  [3:0]a;
   input wire  [3:0]b;
   output wire [3:0]y;
endmodule

module adder_tb;
   reg  [3:0]a;
   reg  [3:0] b;
   wire [3:0] y;
   integer ai, bi;

   adder dut(a, b, y);

   initial begin
      for (ai = 0; ai < 16; ai = ai + 1) begin
	 a = ai;
	 for (bi = 0; bi < 16; bi = bi + 1) begin
	    b = bi;
	    #20;
	    if (y != a + b) begin
	       $display("Fail: %d + %d = %d!", a, b, y);
	       $finish;
	    end;
	 end;
      end;
      $display("Adder OK");
      $finish;
   end; // initial begin
endmodule
