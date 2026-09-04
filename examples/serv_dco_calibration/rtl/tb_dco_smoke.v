`timescale 1ns / 1ps

module tb_dco_smoke (
    input        enable,
    input  [3:0] trim,
    output       osc
);
    dco_core dco (
        .enable(enable),
        .trim(trim),
        .osc(osc)
    );
endmodule
