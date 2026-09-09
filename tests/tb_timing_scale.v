// Timescale is prepended by the runner. Delays use unit suffixes so a 2 ns
// analog delay stays 2 ns when the module unit is 1ps, 1ns, 1us, …

module test_cir(
    input A0,
    input A1,
    output Y0
);
endmodule

module tb_timing_scale;
    reg A0;
    reg A1;
    wire Y0;

    test_cir test_cir (
        .A0(A0),
        .A1(A1),
        .Y0(Y0)
    );

    task check;
        input expected;
        input [8*64-1:0] label;
        begin
            if (Y0 !== expected) begin
                $fatal(1, "%0s: got %b expected %b", label, Y0, expected);
            end
        end
    endtask

    initial begin
        A0 = 1'b0;
        A1 = 1'b0;
        #20ns;
        check(1'b0, "settle");
        A0 = 1'b1;
        #1ns;
        check(1'b0, "1ns-before-delay");
        // 5 ns is well after the 2 ns analog delay. 3 ns is enough on Icarus
        // at 1 ns precision; Verilator still has the bit clear at 3 ns.
        #4ns;
        check(1'b1, "5ns-after-step");
        A0 = 1'b0;
        #1ns;
        check(1'b1, "fall-1ns");
        #4ns;
        check(1'b0, "fall-5ns");
        $display("tb_timing_scale passed");
        $finish;
    end
endmodule
