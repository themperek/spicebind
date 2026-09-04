`timescale 1ns / 1ps

// Count DCO rising edges over a fixed reference-clock window.
// The oscillator is faster than the CPU clock, so the counter is clocked by osc.
module dco_measure #(
    parameter WARMUP  = 4,
    parameter WINDOW  = 16,
    parameter SETTLE  = 2
) (
    input             clk,
    input             rst,
    input             start,
    input             osc,
    output reg        enable,
    output            busy,
    output reg        done,
    output reg [31:0] count
);
    localparam S_IDLE    = 3'd0;
    localparam S_WARMUP  = 3'd1;
    localparam S_MEASURE = 3'd2;
    localparam S_SETTLE  = 3'd3;

    reg [2:0]  state;
    reg [15:0] timer;
    reg [31:0] edges;
    reg        measuring;
    reg        clear_edges;

    assign busy = (state != S_IDLE);

    always @(posedge osc or posedge rst or posedge clear_edges) begin
        if (rst || clear_edges)
            edges <= 32'd0;
        else if (measuring)
            edges <= edges + 32'd1;
    end

    always @(posedge clk) begin
        if (rst) begin
            state       <= S_IDLE;
            enable      <= 1'b0;
            done        <= 1'b0;
            count       <= 32'd0;
            timer       <= 16'd0;
            measuring   <= 1'b0;
            clear_edges <= 1'b0;
        end else begin
            clear_edges <= 1'b0;
            case (state)
                S_IDLE: begin
                    enable    <= 1'b0;
                    measuring <= 1'b0;
                    if (start) begin
                        done   <= 1'b0;
                        enable <= 1'b1;
                        timer  <= WARMUP[15:0];
                        state  <= S_WARMUP;
                    end
                end
                S_WARMUP: begin
                    enable    <= 1'b1;
                    measuring <= 1'b0;
                    if (timer == 16'd0) begin
                        clear_edges <= 1'b1;
                        measuring   <= 1'b1;
                        timer       <= WINDOW[15:0];
                        state       <= S_MEASURE;
                    end else
                        timer <= timer - 16'd1;
                end
                S_MEASURE: begin
                    enable    <= 1'b1;
                    measuring <= 1'b1;
                    if (timer == 16'd0) begin
                        count     <= edges;
                        enable    <= 1'b0;
                        measuring <= 1'b0;
                        timer     <= SETTLE[15:0];
                        state     <= S_SETTLE;
                    end else
                        timer <= timer - 16'd1;
                end
                S_SETTLE: begin
                    enable    <= 1'b0;
                    measuring <= 1'b0;
                    if (timer == 16'd0) begin
                        done  <= 1'b1;
                        state <= S_IDLE;
                    end else
                        timer <= timer - 16'd1;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
