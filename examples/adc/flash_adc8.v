// flash_adc8.v
//
// 8-bit (256-level) flash ADC – behavioural model
// Uses `real` everywhere: good for mixed-signal verification, *not* synthesizable.
//
// vin ∈ [0.0, VREF] where VREF = 1.0 (change as you like)
// Code is straight binary (000…255)
//
// Compile with a simulator that supports IEEE Verilog-2001 real data types


`timescale 1ns/1ns
module flash_adc8(
    input  real vin,          // analog input
    output reg [7:0] code     // digital output
);

    `ifdef VERILOG_MODEL
        // =========================================================================
        // NOTES
        //   * Real thresholds are pre-computed at elaboration: T[i] = (i+0.5)/256
        //   * Conversion is done with one always_comb (single clockless flash step)
        // =========================================================================
        real thresholds [0:255];
        real offset_msb = 0.005;

        // Elaborate threshold ladder
        initial begin : build_ladder
            integer i;
            for (i = 0; i < 256; i = i + 1) begin
                thresholds[i] = (i + 0.5) / 256.0;
                if (i > 127) begin
                    thresholds[i] = thresholds[i]+offset_msb;
                end
            end
        end

        // Combinational conversion (behavioural)
        always @* begin : convert
            integer k;
            code = 8'hFF;               // default clip high
            for (k = 0; k < 256; k = k + 1) begin
                if (vin  < thresholds[k]) begin
                    code = k[7:0];
                    disable convert;    // exit the loop
                end
            end
        end
    `endif

    initial begin
        $dumpfile("flash_adc8.vcd");
        $dumpvars (0);
    end

endmodule
