`timescale 1ns/1ps

module test_cir(
        input real adc_in,
        output wire [7:0] adc_out,

        input wire [7:0] dac_in,
        output real dac_out,

        input wire pwmin,
        output wire pwmout
    );

endmodule

module tb();

    real adc_in;
    wire real dac_out;
    wire [7:0] adc_out;
    reg  [7:0] dac_in;
    wire pwm_in;
    wire pwm_out;

    test_cir test_cir (
        .adc_in(adc_in),
        .adc_out(adc_out),

        .dac_in(dac_in),
        .dac_out(dac_out),

        .pwmin(pwm_in),
        .pwmout(pwm_out)
    );

    initial begin
        $dumpfile("dump.vcd");
        $dumpvars (0);
    end

endmodule
