`timescale 1ns/1ps

module flash_adc8_tb;

    //------------------------------------------------------------------
    // Parameters – change as you like
    //------------------------------------------------------------------
    real  VREF      = 1.0;        // full-scale reference
    real  FS        = 50e6;       // “sample rate” (50 MHz) – for timing only
    real  FIN       = FS / 17.0;  // input tone (coherent with 4096 samples)
    int   NSAMPLES  = 4096;       // how many codes to capture

    // Derived constants
    real  PI        = 3.141592653589793;
    real  PHASE_INC = 2.0 * PI * FIN / FS;  // Δphase per sample (rad)
    time  DT        = time'(1e9 / FS);      // 1/FS in nanoseconds (20 ns)

    //------------------------------------------------------------------
    // DUT connections
    //------------------------------------------------------------------
    real vin;
    wire [7:0] code;

    flash_adc8 dut (
        .vin  (vin),
        .code (code)
    );

    real phase = 0.0;

    //------------------------------------------------------------------
    // Stimulus + dump
    //------------------------------------------------------------------
    initial begin
        $display("time [ns] | vin       | code");
        $display("--------------------------------");


        repeat (NSAMPLES) begin
            // Full-scale, mid-rise sine in the 0 … VREF range
            vin = 0.5 * VREF * (1.0 + $sin(phase));

            // Wait long enough for combinational evaluation
            #(DT);

            // Output one line per sample
            $display("%8t | %0.6f | 0x%0h", $time, vin, code);

            phase = phase + PHASE_INC;
        end

        $finish;
    end

endmodule
