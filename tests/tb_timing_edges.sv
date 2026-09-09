`timescale 1ns/1ps

// No-cocotb delay-chain timing. Analog bits are delayed 2, 4, … 16 ns.
// Select a case with +CASE=<name> so each pytest run is a fresh analog sim.

module test_cir(
    input real adc_in,
    output wire [7:0] adc_out,
    input wire [7:0] dac_in,
    output real dac_out,
    input wire pwmin,
    output wire pwmout
);
endmodule

module tb_timing_edges;
    real adc_in;
    real dac_out;
    wire [7:0] adc_out;
    reg [7:0] dac_in;
    reg pwm_in;
    wire pwm_out;
    integer hammer;
    reg [8*32-1:0] case_name;

    test_cir test_cir (
        .adc_in(adc_in),
        .adc_out(adc_out),
        .dac_in(dac_in),
        .dac_out(dac_out),
        .pwmin(pwm_in),
        .pwmout(pwm_out)
    );

    task automatic check(input logic [7:0] expected, input string label);
        if (adc_out !== expected) begin
            $fatal(1, "%s: got %h expected %h (CASE=%0s)", label, adc_out, expected, case_name);
        end
    endtask

    // Conservative wait: delay plus one analog .tran step (100 ps). A plain
    // #2 can resume before VPI has put analog outputs (cocotb ReadWrite waits
    // for that put). quiet_edges_raw / quiet_edges_nba test the user forms.
    task automatic after_ns(input real ns);
        #(ns);
        #0.1;
    endtask

    task automatic settle_zero;
        adc_in = 0.0;
        dac_in = 0;
        pwm_in = 0;
        #20;
        check(8'd0, "settle");
    endtask

    task automatic rise_fall_on_edges;
        integer i;
        logic [7:0] exp;
        settle_zero();
        adc_in = 1.0;
        exp = 8'd1;
        for (i = 0; i < 8; i = i + 1) begin
            after_ns(2);
            check(exp, "rise-edge");
            exp = {exp[6:0], 1'b1};
        end
        adc_in = 0.0;
        exp = 8'hFE;
        for (i = 0; i < 8; i = i + 1) begin
            after_ns(2);
            check(exp, "fall-edge");
            exp = {exp[6:0], 1'b0};
        end
    endtask

    task automatic rise_fall_between_edges;
        integer i;
        logic [7:0] exp;
        settle_zero();
        adc_in = 1.0;
        exp = 8'd0;
        for (i = 0; i < 10; i = i + 1) begin
            if (i == 0) #1.5;
            else #2;
            check(exp, "rise-between");
            if (exp != 8'hFF) exp = {exp[6:0], 1'b1};
        end
        adc_in = 0.0;
        exp = 8'hFF;
        for (i = 0; i < 10; i = i + 1) begin
            if (i == 0) #1.5;
            else #2;
            check(exp, "fall-between");
            if (exp != 8'h00) exp = {exp[6:0], 1'b0};
        end
    endtask

    task automatic rise_fall_on_edges_raw;
        integer i;
        logic [7:0] exp;
        settle_zero();
        adc_in = 1.0;
        exp = 8'd1;
        for (i = 0; i < 8; i = i + 1) begin
            #2;
            check(exp, "rise-edge-raw");
            exp = {exp[6:0], 1'b1};
        end
        adc_in = 0.0;
        exp = 8'hFE;
        for (i = 0; i < 8; i = i + 1) begin
            #2;
            check(exp, "fall-edge-raw");
            exp = {exp[6:0], 1'b0};
        end
    endtask

    task automatic rise_fall_on_edges_nba;
        integer i;
        logic [7:0] exp;
        settle_zero();
        adc_in = 1.0;
        exp = 8'd1;
        for (i = 0; i < 8; i = i + 1) begin
            #2;
            #0;
            check(exp, "rise-edge-nba");
            exp = {exp[6:0], 1'b1};
        end
        adc_in = 0.0;
        exp = 8'hFE;
        for (i = 0; i < 8; i = i + 1) begin
            #2;
            #0;
            check(exp, "fall-edge-nba");
            exp = {exp[6:0], 1'b0};
        end
    endtask

    task automatic just_before_and_at;
        settle_zero();
        adc_in = 1.0;
        #1.9;
        check(8'd0, "before-2ns");
        after_ns(0.1);
        check(8'd1, "visible-after-2ns");
        #1.9;
        check(8'd1, "before-4ns");
        after_ns(0.1);
        check(8'd3, "visible-after-4ns");
    endtask

    task automatic offgrid_input;
        settle_zero();
        #0.37;
        adc_in = 1.0;
        #1.9;
        check(8'd0, "offgrid-before-2ns");
        after_ns(0.1);
        check(8'd1, "offgrid-visible-after-2ns");
    endtask

    task automatic short_pulse;
        settle_zero();
        adc_in = 1.0;
        #1;
        adc_in = 0.0;
        #5;
        check(8'd0, "short-pulse leftover");
    endtask

    initial begin
        adc_in = 0.0;
        dac_in = 0;
        pwm_in = 0;
        hammer = 0;
        if (!$value$plusargs("CASE=%s", case_name)) begin
            case_name = "quiet_edges";
        end
        hammer = (case_name == "dac_edges" || case_name == "dac_before_at"
            || case_name == "repeat_dac");
        fork
            begin
                if (hammer) forever begin
                    dac_in = (dac_in == 8'h55) ? 8'hAA : 8'h55;
                    pwm_in = ~pwm_in;
                    #1;
                end
            end
            begin
                case (case_name)
                    "quiet_edges": rise_fall_on_edges();
                    "quiet_edges_raw": rise_fall_on_edges_raw();
                    "quiet_edges_nba": rise_fall_on_edges_nba();
                    "between_edges": rise_fall_between_edges();
                    "before_at": just_before_and_at();
                    "dac_edges": rise_fall_on_edges();
                    "dac_before_at": just_before_and_at();
                    "offgrid": offgrid_input();
                    "short_pulse": short_pulse();
                    "repeat_dac": begin
                        repeat (5) rise_fall_on_edges();
                    end
                    default: $fatal(1, "unknown CASE=%s", case_name);
                endcase
                $display("tb_timing_edges %s passed", case_name);
                $finish;
            end
        join
    end
endmodule
