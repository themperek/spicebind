`timescale 1ns/1ps

module adc_core(
    input real vin,
    output [7:0] code,
    input range0,
    input range1
);
    // empty - replaced by SPICE
endmodule

module spi_adc(
    input sclk,
    input mosi,
    output miso,
    input cs,
    input real vin
);
    // internal wires for ADC connection
    wire [7:0] code;
    reg [1:0] range = 0;

    // instantiate analog ADC core
    adc_core adc_inst(
        .vin(vin),
        .code(code),
        .range0(range[0]),
        .range1(range[1])
    );

    // SPI logic
    reg [7:0] mosi_shift = 0;
    reg [7:0] miso_shift = 0;
    reg [3:0] bit_cnt = 0;

    always @(posedge sclk or posedge cs) begin
        if (cs) begin
            bit_cnt <= 0;
        end else begin
            mosi_shift <= {mosi_shift[6:0], mosi};
            bit_cnt <= bit_cnt + 1;
        end
    end

    always @(negedge sclk or posedge cs) begin
        if (cs) begin
            miso_shift <= code;
        end else begin
            miso_shift <= {miso_shift[6:0], 1'b0};
        end
    end

    assign miso = miso_shift[7];

    always @(posedge cs) begin
        range <= mosi_shift[1:0];
    end

endmodule
