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

module tb_sv #(
    parameter real VCC = 1.0,
    parameter bit EXPECT_FAILURE = 0
);
    real adc_in;
    wire real dac_out;
    wire [7:0] adc_out;
    reg [7:0] dac_in;
    reg pwm_in;
    wire pwm_out;

    test_cir test_cir (
        .adc_in(adc_in),
        .adc_out(adc_out),
        .dac_in(dac_in),
        .dac_out(dac_out),
        .pwmin(pwm_in),
        .pwmout(pwm_out)
    );

    task automatic check_adc(input logic [7:0] expected, input string label);
        if (adc_out !== expected) begin
            $fatal(1, "ADC %s: got %h, expected %h", label, adc_out, expected);
        end
    endtask

    task automatic check_dac(input integer expected, input string label);
        integer actual;
        actual = $rtoi((dac_out - 0.00001) / (VCC / 256.0));
        if (actual != expected) begin
            $fatal(1, "DAC %s: got %0d (voltage %0f), expected %0d", label, actual, dac_out, expected);
        end
    endtask

    task automatic check_pwm(input logic expected, input string label);
        if (pwm_out !== expected) begin
            $fatal(1, "PWM %s: got %b, expected %b", label, pwm_out, expected);
        end
    endtask

    task automatic run_adc_test();
        integer i;
        integer expected;

        adc_in = 0.0;
        #20;
        check_adc(8'd0, "initial zero");

        adc_in = 1.0;
        #20;
        check_adc(8'd255, "full scale");

        adc_in = 0.0;
        #20;
        check_adc(8'd0, "return to zero");

        adc_in = 1.0;
        for (i = 0; i < 10; i = i + 1) begin
            #2;
            case (i)
                0: expected = 0;
                1: expected = 1;
                2: expected = 3;
                3: expected = 7;
                4: expected = 15;
                5: expected = 31;
                6: expected = 63;
                7: expected = 127;
                default: expected = 255;
            endcase
            check_adc(expected[7:0], "rising delayed bits");
        end

        adc_in = 0.0;
        for (i = 0; i < 10; i = i + 1) begin
            #2;
            case (i)
                0: expected = 255;
                1: expected = 254;
                2: expected = 252;
                3: expected = 248;
                4: expected = 240;
                5: expected = 224;
                6: expected = 192;
                7: expected = 128;
                default: expected = 0;
            endcase
            check_adc(expected[7:0], "falling delayed bits");
        end

        for (i = 0; i < 1000; i = i + 1) begin
            adc_in = i * 0.001 - 0.00001;
            #(20 + $urandom_range(0, 10));
            expected = $rtoi(adc_in / (1.0 / 256.0));
            check_adc(expected[7:0], "rising ramp");
        end

        for (i = 0; i < 1000; i = i + 1) begin
            adc_in = 1.0 - i * 0.001 - 0.00001;
            #(20 + $urandom_range(0, 10));
            expected = $rtoi(adc_in / (1.0 / 256.0));
            check_adc(expected[7:0], "falling ramp");
        end
    endtask

    task automatic run_dac_test();
        integer i;

        dac_in = 0;
        #11;
        check_dac(0, "initial zero");

        dac_in = 255;
        #11;
        check_dac(255, "full scale");

        for (i = 0; i < 256; i = i + 1) begin
            dac_in = i;
            #(8 + $urandom_range(0, 92));
            check_dac(i, "rising ramp");
        end

        for (i = 255; i >= 0; i = i - 1) begin
            dac_in = i;
            #(8 + $urandom_range(0, 92));
            check_dac(i, "falling ramp");
        end
    endtask

    task automatic run_pwm_test();
        integer i;

        pwm_in = 0;
        #10us;
        check_pwm(1'b0, "initial zero");

        pwm_in = 1;
        #10us;
        check_pwm(1'b1, "initial one");

        for (i = 0; i < 100; i = i + 1) begin
            pwm_in = 1;
            #50;
            pwm_in = 0;
            #50;
        end
        check_pwm(1'bx, "50 percent duty cycle");

        for (i = 0; i < 100; i = i + 1) begin
            pwm_in = 1;
            #20;
            pwm_in = 0;
            #80;
        end
        check_pwm(1'b0, "20 percent duty cycle");

        for (i = 0; i < 100; i = i + 1) begin
            pwm_in = 1;
            #80;
            pwm_in = 0;
            #20;
        end
        check_pwm(1'b1, "80 percent duty cycle");
    endtask

    initial begin
        if (EXPECT_FAILURE) begin
            #1;
            check_adc(8'd1, "intentional failure");
        end
        else begin
            fork
                run_adc_test();
                run_dac_test();
                run_pwm_test();
            join
            $display("SystemVerilog mixed-signal test passed");
        end
        $finish;
    end
endmodule
