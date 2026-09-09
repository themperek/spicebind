`timescale 1ns/1ps

// Verilog (no cocotb, no real) 2 ns analog delay on Y0.
// +CASE=0 quiet, 1 hammer, 2 off-grid, 3 short pulse, 4 2 ns pulse

module test_cir(
    input A0,
    input A1,
    output Y0
);
endmodule

module tb_timing_bit;
    reg A0;
    reg A1;
    wire Y0;
    integer case_id;
    integer hammer;

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
                $fatal(1, "%0s: got %b expected %b (CASE=%0d)", label, Y0, expected, case_id);
            end
        end
    endtask

    task settle_zero;
        begin
            A0 = 1'b0;
            A1 = 1'b0;
            #20;
            check(1'b0, "settle");
        end
    endtask

    initial begin
        A0 = 1'b0;
        A1 = 1'b0;
        hammer = 0;
        if (!$value$plusargs("CASE=%d", case_id)) begin
            case_id = 0;
        end
        if (case_id == 1) begin
            hammer = 1;
        end
        fork
            begin
                if (hammer) forever begin
                    A1 = ~A1;
                    #1;
                end
            end
            begin
                case (case_id)
                    0, 1: begin
                        settle_zero();
                        A0 = 1'b1;
                        #1.9;
                        check(1'b0, "before-2ns");
                        #0.2;
                        check(1'b1, "visible-after-2ns");
                        A0 = 1'b0;
                        #1.9;
                        check(1'b1, "fall-before-2ns");
                        #0.2;
                        check(1'b0, "fall-visible-after-2ns");
                    end
                    4: begin
                        // User form: wait the delay, then sample (no extra analog step).
                        settle_zero();
                        A0 = 1'b1;
                        #2;
                        check(1'b1, "raw-2ns");
                        A0 = 1'b0;
                        #2;
                        check(1'b0, "raw-fall-2ns");
                    end
                    2: begin
                        settle_zero();
                        #0.37;
                        A0 = 1'b1;
                        #1.9;
                        check(1'b0, "offgrid-before-2ns");
                        #0.2;
                        check(1'b1, "offgrid-visible-after-2ns");
                    end
                    3: begin
                        settle_zero();
                        A0 = 1'b1;
                        #1;
                        A0 = 1'b0;
                        #5;
                        check(1'b0, "short-pulse leftover");
                    end
                    default: $fatal(1, "unknown CASE=%0d", case_id);
                endcase
                $display("tb_timing_bit CASE=%0d passed", case_id);
                $finish;
            end
        join
    end
endmodule
