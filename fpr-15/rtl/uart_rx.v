/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: uart_rx.v
 * Purpose: 230,400 baud UART receiver at 100 MHz clock with stop-bit verification
 *          and framing error detection.
 *          Baud divisor = 100,000,000 / 230,400 = 434 system clock cycles per bit.
 */

`timescale 1ns / 1ps

module uart_rx #(
    parameter CLK_FREQ_HZ = 100000000,
    parameter BAUD_RATE   = 230400
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rxd,
    
    output reg        byte_valid,
    output reg  [7:0] byte_data,
    output reg        frame_err
);

    localparam CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE; // 434
    localparam HALF_BIT     = CLKS_PER_BIT / 2;         // 217

    localparam STATE_IDLE  = 2'b00;
    localparam STATE_START = 2'b01;
    localparam STATE_DATA  = 2'b10;
    localparam STATE_STOP  = 2'b11;

    reg [1:0]  state;
    reg [11:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  rx_shift;

    // Double-flop synchronizer for asynchronous RX input
    reg rxd_sync1, rxd_sync2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rxd_sync1 <= 1'b1;
            rxd_sync2 <= 1'b1;
        end else begin
            rxd_sync1 <= rxd;
            rxd_sync2 <= rxd_sync1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state             <= STATE_IDLE;
            clk_count         <= 12'd0;
            bit_index         <= 3'd0;
            rx_shift          <= 8'd0;
            byte_valid        <= 1'b0;
            byte_data         <= 8'd0;
            frame_err         <= 1'b0;
        end else begin
            byte_valid <= 1'b0;
            frame_err  <= 1'b0;

            case (state)
                STATE_IDLE: begin
                    clk_count <= 12'd0;
                    bit_index <= 3'd0;
                    if (rxd_sync2 == 1'b0) begin // Start bit falling edge detected
                        state <= STATE_START;
                    end
                end

                STATE_START: begin
                    // Verify start bit at center sample (HALF_BIT = 217)
                    if (clk_count == HALF_BIT) begin
                        if (rxd_sync2 == 1'b0) begin // Valid start bit
                            clk_count <= 12'd0;
                            state     <= STATE_DATA;
                        end else begin // Glitch / false start bit: abort back to IDLE
                            state <= STATE_IDLE;
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                STATE_DATA: begin
                    // Sample data bits at full bit period (CLKS_PER_BIT - 1)
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 12'd0;
                        rx_shift[bit_index] <= rxd_sync2;
                        if (bit_index == 3'd7) begin
                            state <= STATE_STOP;
                        end else begin
                            bit_index <= bit_index + 1'b1;
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end

                STATE_STOP: begin
                    // clk_count restarts at the CENTER of data bit 7, so waiting a full
                    // bit period lands at the CENTER of the stop bit (most tolerant point).
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        state     <= STATE_IDLE;
                        clk_count <= 12'd0;
                        if (rxd_sync2 == 1'b1) begin
                            byte_valid <= 1'b1;   // stop bit high: valid byte
                            byte_data  <= rx_shift;
                        end else begin
                            frame_err  <= 1'b1;   // stop bit low: framing error, discard
                        end
                    end else begin
                        clk_count <= clk_count + 1'b1;
                    end
                end
            endcase
        end
    end

endmodule
