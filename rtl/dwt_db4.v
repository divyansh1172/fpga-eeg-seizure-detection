/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: dwt_db4
 * Purpose: 5-level Daubechies-4 (db4) analysis filter bank cascade for 22 EEG channels.
 *          Implements dyadic multiresolution decomposition:
 *            Level 1: 128 Hz Nyquist (approx feeds Level 2)
 *            Level 2:  64 Hz Nyquist (approx feeds Level 3)
 *            Level 3:  32 Hz Nyquist -> Detail is D3 (16-32 Hz Beta/Gamma) [RETAINED]
 *            Level 4:  16 Hz Nyquist -> Detail is D4 (8-16 Hz Alpha/Spindles) [RETAINED]
 *            Level 5:   8 Hz Nyquist -> Detail is D5 (4-8 Hz Theta) [RETAINED]
 *                                    -> Approx is A5 (0-4 Hz Delta) [RETAINED]
 *          Each level is an instance of dwt_level with per-channel state RAM and
 *          per-channel decimation phase.
 *          Outputs are tagged with channel ID, subband ID (0: D3, 1: D4, 2: D5, 3: A5),
 *          and individual one-hot pulses (valid_d3, valid_d4, valid_d5, valid_a5).
 *          Internal FIFO queue ensures clean serialization without contention.
 */

`timescale 1ns / 1ps

module dwt_db4 #(
    parameter DATA_WIDTH   = 16,
    parameter NUM_CHANNELS = 22
)(
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          sample_valid,
    input  wire [4:0]                    ch_in,
    input  wire signed [DATA_WIDTH-1:0]  sample_in,
    
    output reg                           out_valid,
    output reg  [4:0]                    ch_out,
    output reg  [1:0]                    subband_id,   // 0: D3, 1: D4, 2: D5, 3: A5
    output reg  signed [DATA_WIDTH-1:0]  coeff_out,
    output reg                           valid_d3,
    output reg                           valid_d4,
    output reg                           valid_d5,
    output reg                           valid_a5,

    // Legacy ports for backwards compatibility
    output wire signed [DATA_WIDTH-1:0]  approx_out,
    output wire signed [DATA_WIDTH-1:0]  detail_out
);

    // =========================================================================
    // 5-Level Cascaded Filter Bank
    // =========================================================================

    // Level 1: 0.5 - 64 Hz (Approx) / 64 - 128 Hz (Detail)
    wire                          l1_out_valid;
    wire [4:0]                    l1_ch_out;
    wire signed [DATA_WIDTH-1:0]  l1_approx;
    wire signed [DATA_WIDTH-1:0]  l1_detail;

    dwt_level #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_lvl1 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(sample_valid),
        .ch_in(ch_in),
        .data_in(sample_in),
        .out_valid(l1_out_valid),
        .ch_out(l1_ch_out),
        .approx_out(l1_approx),
        .detail_out(l1_detail)
    );

    // Level 2: 0.5 - 32 Hz (Approx) / 32 - 64 Hz (Detail)
    wire                          l2_out_valid;
    wire [4:0]                    l2_ch_out;
    wire signed [DATA_WIDTH-1:0]  l2_approx;
    wire signed [DATA_WIDTH-1:0]  l2_detail;

    dwt_level #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_lvl2 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(l1_out_valid),
        .ch_in(l1_ch_out),
        .data_in(l1_approx),
        .out_valid(l2_out_valid),
        .ch_out(l2_ch_out),
        .approx_out(l2_approx),
        .detail_out(l2_detail)
    );

    // Level 3: 0.5 - 16 Hz (Approx) / 16 - 32 Hz (Detail -> D3)
    wire                          l3_out_valid;
    wire [4:0]                    l3_ch_out;
    wire signed [DATA_WIDTH-1:0]  l3_approx;
    wire signed [DATA_WIDTH-1:0]  l3_detail;

    dwt_level #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_lvl3 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(l2_out_valid),
        .ch_in(l2_ch_out),
        .data_in(l2_approx),
        .out_valid(l3_out_valid),
        .ch_out(l3_ch_out),
        .approx_out(l3_approx),
        .detail_out(l3_detail)
    );

    // Level 4: 0.5 - 8 Hz (Approx) / 8 - 16 Hz (Detail -> D4)
    wire                          l4_out_valid;
    wire [4:0]                    l4_ch_out;
    wire signed [DATA_WIDTH-1:0]  l4_approx;
    wire signed [DATA_WIDTH-1:0]  l4_detail;

    dwt_level #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_lvl4 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(l3_out_valid),
        .ch_in(l3_ch_out),
        .data_in(l3_approx),
        .out_valid(l4_out_valid),
        .ch_out(l4_ch_out),
        .approx_out(l4_approx),
        .detail_out(l4_detail)
    );

    // Level 5: 0.5 - 4 Hz (Approx -> A5) / 4 - 8 Hz (Detail -> D5)
    wire                          l5_out_valid;
    wire [4:0]                    l5_ch_out;
    wire signed [DATA_WIDTH-1:0]  l5_approx;
    wire signed [DATA_WIDTH-1:0]  l5_detail;

    dwt_level #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_lvl5 (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(l4_out_valid),
        .ch_in(l4_ch_out),
        .data_in(l4_approx),
        .out_valid(l5_out_valid),
        .ch_out(l5_ch_out),
        .approx_out(l5_approx),
        .detail_out(l5_detail)
    );

    // =========================================================================
    // Output Queue and Serialization
    // =========================================================================
    // Entry format: {subband_id[1:0], channel_id[4:0], coeff[15:0]} = 23 bits
    reg [22:0] queue_mem [0:7];
    reg [2:0]  q_head;
    reg [2:0]  q_tail;
    reg [3:0]  q_count;

    wire pop_valid = (q_count > 4'd0);
    wire [22:0] top_item = queue_mem[q_tail];

    integer qi;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (qi = 0; qi < 8; qi = qi + 1) begin
                queue_mem[qi] <= 23'd0;
            end
            q_head     <= 3'd0;
            q_tail     <= 3'd0;
            q_count    <= 4'd0;
            out_valid  <= 1'b0;
            ch_out     <= 5'd0;
            subband_id <= 2'd0;
            coeff_out  <= {DATA_WIDTH{1'b0}};
            valid_d3   <= 1'b0;
            valid_d4   <= 1'b0;
            valid_d5   <= 1'b0;
            valid_a5   <= 1'b0;
        end else begin
            // 1. Output popping
            if (pop_valid) begin
                out_valid  <= 1'b1;
                subband_id <= top_item[22:21];
                ch_out     <= top_item[20:16];
                coeff_out  <= top_item[15:0];
                valid_d3   <= (top_item[22:21] == 2'd0);
                valid_d4   <= (top_item[22:21] == 2'd1);
                valid_d5   <= (top_item[22:21] == 2'd2);
                valid_a5   <= (top_item[22:21] == 2'd3);
                q_tail     <= q_tail + 3'd1;
            end else begin
                out_valid  <= 1'b0;
                valid_d3   <= 1'b0;
                valid_d4   <= 1'b0;
                valid_d5   <= 1'b0;
                valid_a5   <= 1'b0;
            end

            // 2. Queue enqueue logic
            if (l5_out_valid) begin
                // Level 5 produces both D5 and A5
                queue_mem[q_head]        <= {2'd2, l5_ch_out, l5_detail};
                queue_mem[q_head + 3'd1] <= {2'd3, l5_ch_out, l5_approx};
                q_head  <= q_head + 3'd2;
                q_count <= q_count + (pop_valid ? 4'd1 : 4'd2);
            end else if (l4_out_valid) begin
                // Level 4 produces D4
                queue_mem[q_head] <= {2'd1, l4_ch_out, l4_detail};
                q_head  <= q_head + 3'd1;
                q_count <= q_count + (pop_valid ? 4'd0 : 4'd1);
            end else if (l3_out_valid) begin
                // Level 3 produces D3
                queue_mem[q_head] <= {2'd0, l3_ch_out, l3_detail};
                q_head  <= q_head + 3'd1;
                q_count <= q_count + (pop_valid ? 4'd0 : 4'd1);
            end else begin
                if (pop_valid) begin
                    q_count <= q_count - 4'd1;
                end
            end
        end
    end

    // Backward compatibility assignments
    assign approx_out = coeff_out;
    assign detail_out = coeff_out;

endmodule
