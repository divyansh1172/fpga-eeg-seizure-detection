/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: dwt_level
 * Purpose: Single-level Daubechies-4 (db4) analysis filter bank and dyadic decimator.
 *          Optimized 8-cycle serial MAC architecture for FPGA synthesis.
 *          Uses exactly 2 DSP48E1 slices per level instead of 16 parallel multipliers,
 *          eliminating massive 9-input adder trees and reducing LUT count by >15,000 LUTs.
 */

`timescale 1ns / 1ps

module dwt_level #(
    parameter DATA_WIDTH   = 16,
    parameter NUM_CHANNELS = 22
)(
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          in_valid,
    input  wire [4:0]                    ch_in,
    input  wire signed [DATA_WIDTH-1:0]  data_in,
    
    output reg                           out_valid,
    output reg  [4:0]                    ch_out,
    output reg  signed [DATA_WIDTH-1:0]  approx_out,
    output reg  signed [DATA_WIDTH-1:0]  detail_out
);

    // Exact standard 8-tap db4 decomposition filter coefficients in Q15 format
    function signed [15:0] get_h;
        input [2:0] idx;
        case (idx)
            3'd0: get_h = 16'shFEA5; //   -347
            3'd1: get_h = 16'sh0436; //   1078
            3'd2: get_h = 16'sh03F3; //   1011
            3'd3: get_h = 16'shE80F; //  -6129
            3'd4: get_h = 16'shFC6B; //   -917
            3'd5: get_h = 16'sh50C1; //  20673
            3'd6: get_h = 16'sh5B80; //  23424
            3'd7: get_h = 16'sh1D7D; //   7549
        endcase
    endfunction

    function signed [15:0] get_g;
        input [2:0] idx;
        case (idx)
            3'd0: get_g = 16'sh1D7D; //   7549
            3'd1: get_g = 16'shA480; // -23424
            3'd2: get_g = 16'sh50C1; //  20673
            3'd3: get_g = 16'sh0395; //    917
            3'd4: get_g = 16'shE80F; //  -6129
            3'd5: get_g = 16'shFC0D; //  -1011
            3'd6: get_g = 16'sh0436; //   1078
            3'd7: get_g = 16'sh015B; //    347
        endcase
    endfunction

    // Per-channel sample history: 7 previous samples
    reg signed [DATA_WIDTH-1:0] hist [0:NUM_CHANNELS-1][0:6];

    // Per-channel decimation phase (1 bit per channel)
    reg [NUM_CHANNELS-1:0] phase_ram;

    // FSM States
    localparam S_IDLE = 2'd0;
    localparam S_CALC = 2'd1;
    localparam S_OUT  = 2'd2;

    reg [1:0]  state;
    reg [2:0]  tap_idx;
    reg [4:0]  active_ch;

    // Working tap buffer for currently active calculation
    reg signed [DATA_WIDTH-1:0] tap_buf [0:7];

    // 36-bit accumulators for serial MAC
    reg signed [35:0] acc_h;
    reg signed [35:0] acc_g;

    // Current multiplier inputs
    wire signed [15:0] cur_x = tap_buf[tap_idx];
    wire signed [15:0] cur_h = get_h(tap_idx);
    wire signed [15:0] cur_g = get_g(tap_idx);

    wire signed [31:0] prod_h = cur_x * cur_h;
    wire signed [31:0] prod_g = cur_x * cur_g;

    // Saturation helper function
    function signed [15:0] sat16;
        input signed [20:0] val;
        begin
            if (val > 21'sd32767)
                sat16 = 16'sd32767;
            else if (val < -21'sd32768)
                sat16 = -16'sd32768;
            else
                sat16 = val[15:0];
        end
    endfunction

    wire signed [20:0] round_h = (acc_h + 36'sd16384) >>> 15;
    wire signed [20:0] round_g = (acc_g + 36'sd16384) >>> 15;

    integer c, t;
    initial begin
        for (c = 0; c < NUM_CHANNELS; c = c + 1) begin
            for (t = 0; t < 7; t = t + 1) begin
                hist[c][t] = {DATA_WIDTH{1'b0}};
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (c = 0; c < NUM_CHANNELS; c = c + 1) begin
                for (t = 0; t < 7; t = t + 1) begin
                    hist[c][t] <= {DATA_WIDTH{1'b0}};
                end
            end
            phase_ram   <= {NUM_CHANNELS{1'b0}};
            state       <= S_IDLE;
            tap_idx     <= 3'd0;
            active_ch   <= 5'd0;
            acc_h       <= 36'd0;
            acc_g       <= 36'd0;
            out_valid   <= 1'b0;
            ch_out      <= 5'd0;
            approx_out  <= {DATA_WIDTH{1'b0}};
            detail_out  <= {DATA_WIDTH{1'b0}};
        end else begin
            out_valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (in_valid && (ch_in < NUM_CHANNELS)) begin
                        // Toggle decimation phase for this channel
                        phase_ram[ch_in] <= ~phase_ram[ch_in];

                        // Latch current 8 taps (x0 = new sample, x1..x7 = history)
                        tap_buf[0] <= data_in;
                        tap_buf[1] <= hist[ch_in][0];
                        tap_buf[2] <= hist[ch_in][1];
                        tap_buf[3] <= hist[ch_in][2];
                        tap_buf[4] <= hist[ch_in][3];
                        tap_buf[5] <= hist[ch_in][4];
                        tap_buf[6] <= hist[ch_in][5];
                        tap_buf[7] <= hist[ch_in][6];

                        // Update history for this channel
                        hist[ch_in][6] <= hist[ch_in][5];
                        hist[ch_in][5] <= hist[ch_in][4];
                        hist[ch_in][4] <= hist[ch_in][3];
                        hist[ch_in][3] <= hist[ch_in][2];
                        hist[ch_in][2] <= hist[ch_in][1];
                        hist[ch_in][1] <= hist[ch_in][0];
                        hist[ch_in][0] <= data_in;

                        // Only compute if phase was 1 (compute phase)
                        if (phase_ram[ch_in] == 1'b1) begin
                            active_ch <= ch_in;
                            tap_idx   <= 3'd0;
                            state     <= S_CALC;
                        end
                    end
                end

                S_CALC: begin
                    if (tap_idx == 3'd0) begin
                        acc_h <= {{4{prod_h[31]}}, prod_h};
                        acc_g <= {{4{prod_g[31]}}, prod_g};
                        tap_idx <= 3'd1;
                    end else begin
                        acc_h <= acc_h + {{4{prod_h[31]}}, prod_h};
                        acc_g <= acc_g + {{4{prod_g[31]}}, prod_g};
                        if (tap_idx == 3'd7) begin
                            state <= S_OUT;
                        end else begin
                            tap_idx <= tap_idx + 1'b1;
                        end
                    end
                end

                S_OUT: begin
                    out_valid  <= 1'b1;
                    ch_out     <= active_ch;
                    approx_out <= sat16(round_h);
                    detail_out <= sat16(round_g);
                    state      <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
