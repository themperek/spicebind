`timescale 1ns / 1ps

module top #(
    parameter MEM_WORDS = 2048,
    parameter INIT_FILE = "firmware.hex",
    parameter WARMUP    = 4,
    parameter WINDOW    = 16,
    parameter SETTLE    = 2
) (
    input  clk,
    input  rst
);
    localparam RF_WIDTH = 2;

    wire [31:0] wb_mem_adr, wb_mem_dat, wb_mem_rdt;
    wire  [3:0] wb_mem_sel;
    wire        wb_mem_we, wb_mem_stb, wb_mem_ack;

    wire [31:0] wb_ext_adr, wb_ext_dat, wb_ext_rdt;
    wire  [3:0] wb_ext_sel;
    wire        wb_ext_we, wb_ext_stb, wb_ext_ack;

    wire [$clog2(32*32/RF_WIDTH)-1:0] rf_waddr, rf_raddr;
    wire [RF_WIDTH-1:0] rf_wdata, rf_rdata;
    wire rf_wen, rf_ren;

    wire [3:0] dco_trim;
    wire       dco_enable;
    wire       dco_osc;

    servile #(
        .width(1),
        .reset_pc(32'h0000_0000),
        .reset_strategy("MINI"),
        .sim(1'b0),
        .debug(1'b0),
        .with_c(1'b0),
        .with_csr(1'b0),
        .with_mdu(1'b0)
    ) u_cpu (
        .i_clk(clk),
        .i_rst(rst),
        .i_timer_irq(1'b0),
        .o_wb_mem_adr(wb_mem_adr),
        .o_wb_mem_dat(wb_mem_dat),
        .o_wb_mem_sel(wb_mem_sel),
        .o_wb_mem_we(wb_mem_we),
        .o_wb_mem_stb(wb_mem_stb),
        .i_wb_mem_rdt(wb_mem_rdt),
        .i_wb_mem_ack(wb_mem_ack),
        .o_wb_ext_adr(wb_ext_adr),
        .o_wb_ext_dat(wb_ext_dat),
        .o_wb_ext_sel(wb_ext_sel),
        .o_wb_ext_we(wb_ext_we),
        .o_wb_ext_stb(wb_ext_stb),
        .i_wb_ext_rdt(wb_ext_rdt),
        .i_wb_ext_ack(wb_ext_ack),
        .o_rf_waddr(rf_waddr),
        .o_rf_wdata(rf_wdata),
        .o_rf_wen(rf_wen),
        .o_rf_raddr(rf_raddr),
        .o_rf_ren(rf_ren),
        .i_rf_rdata(rf_rdata)
    );

    serv_rf_ram #(
        .width(RF_WIDTH),
        .csr_regs(0)
    ) u_rf (
        .i_clk(clk),
        .i_waddr(rf_waddr),
        .i_wdata(rf_wdata),
        .i_wen(rf_wen),
        .i_raddr(rf_raddr),
        .i_ren(rf_ren),
        .o_rdata(rf_rdata)
    );

    simple_ram #(
        .DEPTH_WORDS(MEM_WORDS),
        .INIT_FILE(INIT_FILE)
    ) u_ram (
        .clk(clk),
        .rst(rst),
        .i_wb_adr(wb_mem_adr),
        .i_wb_dat(wb_mem_dat),
        .i_wb_sel(wb_mem_sel),
        .i_wb_we(wb_mem_we),
        .i_wb_stb(wb_mem_stb),
        .o_wb_rdt(wb_mem_rdt),
        .o_wb_ack(wb_mem_ack)
    );

    dco_peripheral #(
        .WARMUP(WARMUP),
        .WINDOW(WINDOW),
        .SETTLE(SETTLE)
    ) u_periph (
        .clk(clk),
        .rst(rst),
        .i_wb_adr(wb_ext_adr),
        .i_wb_dat(wb_ext_dat),
        .i_wb_sel(wb_ext_sel),
        .i_wb_we(wb_ext_we),
        .i_wb_stb(wb_ext_stb),
        .o_wb_rdt(wb_ext_rdt),
        .o_wb_ack(wb_ext_ack),
        .o_trim(dco_trim),
        .o_enable(dco_enable),
        .i_osc(dco_osc)
    );

    dco_core u_dco (
        .enable(dco_enable),
        .trim(dco_trim),
        .osc(dco_osc)
    );
endmodule
