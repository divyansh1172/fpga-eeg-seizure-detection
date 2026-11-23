/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: uart_tx
 * Purpose: Compact 8N1 UART transmitter for telemetry to host PC.
 *          Transmits an alert status byte (e.g. 0xA5) when an alarm triggers.
 *          Maintains standard UART idle-high line state (1'b1), completely
 *          eliminating permanent break conditions on the TX pin.
 */

`timescale 1ns / 1ps

module uart_tx #(
    parameter CLK_FREQ_HZ = 100000000,
    parameter BAUD_RATE   = 230400
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    
    output reg        tx_busy,
    output reg        txd
);

    localparam CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE; // 434 clock cycles @ 100MHz / 230400

    reg [8:0]  clk_cnt;
    reg [3:0]  bit_idx;
    reg [9:0]  shift_reg; // {stop_bit (1), data (8), start_bit (0)}

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_cnt   <= 9'd0;
            bit_idx   <= 4'd0;
            shift_reg <= 10'h3FF;
            tx_busy   <= 1'b0;
            txd       <= 1'b1; // UART Idle-High
        end else begin
            if (!tx_busy) begin
                txd <= 1'b1;
                if (tx_start) begin
                    shift_reg <= {1'b1, tx_data, 1'b0};
                    tx_busy   <= 1'b1;
                    clk_cnt   <= 9'd0;
                    bit_idx   <= 4'd0;
                    txd       <= 1'b0; // start bit
                end
            end else begin
                if (clk_cnt == CLKS_PER_BIT - 1) begin
                    clk_cnt <= 9'd0;
                    if (bit_idx == 4'd9) begin
                        tx_busy <= 1'b0;
                        txd     <= 1'b1; // return to idle high
                    end else begin
                        bit_idx   <= bit_idx + 1'b1;
                        txd       <= shift_reg[bit_idx + 1'b1];
                    end
                end else begin
                    clk_cnt <= clk_cnt + 1'b1;
                end
            end
        end
    end

endmodule
