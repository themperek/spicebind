`timescale 1ns / 1ps

// Wishbone-mapped DCO control / result registers.
module dco_peripheral #(
    parameter WARMUP = 4,
    parameter WINDOW = 16,
    parameter SETTLE = 2
) (
    input             clk,
    input             rst,
    input      [31:0] i_wb_adr,
    input      [31:0] i_wb_dat,
    input       [3:0] i_wb_sel,
    input             i_wb_we,
    input             i_wb_stb,
    output reg [31:0] o_wb_rdt,
    output reg        o_wb_ack,
    output      [3:0] o_trim,
    output            o_enable,
    input             i_osc
);
    localparam ADR_TRIM       = 4'h0;
    localparam ADR_CTRL       = 4'h1;
    localparam ADR_STATUS     = 4'h2;
    localparam ADR_COUNT      = 4'h3;
    localparam ADR_RESULT     = 4'h4;
    localparam ADR_FINAL_CNT  = 4'h5;
    localparam ADR_ITERS      = 4'h6;

    reg  [3:0] trim;
    reg        start_pulse;
    wire       busy;
    wire       done;
    wire [31:0] meas_count;

    reg [31:0] fw_result;
    reg [31:0] fw_final_count;
    reg [31:0] fw_iterations;

    assign o_trim = trim;

    dco_measure #(
        .WARMUP(WARMUP),
        .WINDOW(WINDOW),
        .SETTLE(SETTLE)
    ) u_meas (
        .clk(clk),
        .rst(rst),
        .start(start_pulse),
        .osc(i_osc),
        .enable(o_enable),
        .busy(busy),
        .done(done),
        .count(meas_count)
    );

    wire [3:0] reg_sel = i_wb_adr[5:2];

    always @(posedge clk) begin
        if (rst) begin
            o_wb_ack        <= 1'b0;
            o_wb_rdt        <= 32'd0;
            trim            <= 4'd0;
            start_pulse     <= 1'b0;
            fw_result       <= 32'd0;
            fw_final_count  <= 32'd0;
            fw_iterations   <= 32'd0;
        end else begin
            o_wb_ack    <= 1'b0;
            start_pulse <= 1'b0;
            if (i_wb_stb && !o_wb_ack) begin
                o_wb_ack <= 1'b1;
                if (i_wb_we) begin
                    case (reg_sel)
                        ADR_TRIM:      trim <= i_wb_dat[3:0];
                        ADR_CTRL:      start_pulse <= i_wb_dat[0];
                        ADR_RESULT:    fw_result <= i_wb_dat;
                        ADR_FINAL_CNT: fw_final_count <= i_wb_dat;
                        ADR_ITERS:     fw_iterations <= i_wb_dat;
                        default: ;
                    endcase
                end else begin
                    case (reg_sel)
                        ADR_TRIM:      o_wb_rdt <= {28'd0, trim};
                        ADR_CTRL:      o_wb_rdt <= 32'd0;
                        ADR_STATUS:    o_wb_rdt <= {30'd0, done, busy};
                        ADR_COUNT:     o_wb_rdt <= meas_count;
                        ADR_RESULT:    o_wb_rdt <= fw_result;
                        ADR_FINAL_CNT: o_wb_rdt <= fw_final_count;
                        ADR_ITERS:     o_wb_rdt <= fw_iterations;
                        default:       o_wb_rdt <= 32'd0;
                    endcase
                end
            end
        end
    end
endmodule
