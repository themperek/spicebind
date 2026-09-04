`timescale 1ns / 1ps

// Behavioral stand-in for dco_core. Higher trim -> higher frequency.
module dco_core (
    input        enable,
    input  [3:0] trim,
    output reg   osc = 1'b0
);
    integer scale;
    integer half_ns;

    initial begin
        scale = 1;
        if ($value$plusargs("DCO_BEH_SCALE=%d", scale) == 0)
            scale = 1;
        if (scale < 1)
            scale = 1;
    end

    always begin
        osc = 1'b0;
        wait (enable === 1'b1);
        begin : run
            while (enable === 1'b1) begin
                half_ns = scale * (9 - (trim >> 1));
                if (half_ns < 2)
                    half_ns = 2;
                repeat (half_ns) begin
                    if (enable !== 1'b1)
                        disable run;
                    #1;
                end
                osc = ~osc;
            end
        end
        osc = 1'b0;
    end
endmodule
