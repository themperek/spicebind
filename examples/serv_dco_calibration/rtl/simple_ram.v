`timescale 1ns / 1ps

// Tiny Wishbone SRAM. $readmemh loads little-endian 32-bit words.
module simple_ram #(
    parameter DEPTH_WORDS = 2048,
    parameter INIT_FILE   = ""
) (
    input             clk,
    input             rst,
    input      [31:0] i_wb_adr,
    input      [31:0] i_wb_dat,
    input       [3:0] i_wb_sel,
    input             i_wb_we,
    input             i_wb_stb,
    output reg [31:0] o_wb_rdt,
    output reg        o_wb_ack
);
    reg [31:0] mem [0:DEPTH_WORDS-1];
    integer i;

    initial begin
        for (i = 0; i < DEPTH_WORDS; i = i + 1)
            mem[i] = 32'd0;
        if (INIT_FILE != "")
            $readmemh(INIT_FILE, mem);
    end

    wire [$clog2(DEPTH_WORDS)-1:0] word_adr = i_wb_adr[$clog2(DEPTH_WORDS)+1:2];

    always @(posedge clk) begin
        if (rst) begin
            o_wb_ack <= 1'b0;
            o_wb_rdt <= 32'd0;
        end else begin
            o_wb_ack <= 1'b0;
            if (i_wb_stb && !o_wb_ack) begin
                o_wb_ack <= 1'b1;
                o_wb_rdt <= mem[word_adr];
                if (i_wb_we) begin
                    if (i_wb_sel[0]) mem[word_adr][7:0]   <= i_wb_dat[7:0];
                    if (i_wb_sel[1]) mem[word_adr][15:8]  <= i_wb_dat[15:8];
                    if (i_wb_sel[2]) mem[word_adr][23:16] <= i_wb_dat[23:16];
                    if (i_wb_sel[3]) mem[word_adr][31:24] <= i_wb_dat[31:24];
                end
            end
        end
    end
endmodule
