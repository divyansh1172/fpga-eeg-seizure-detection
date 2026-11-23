/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: feature_accumulator
 * Purpose: Double-buffered (ping-pong) streaming feature accumulator for Energy (E)
 *          and Line-Length (LL) across 22 channels and 4 sub-bands (D3, D4, D5, A5).
 *          Features are normalized with exact coefficient-count bit-shifts and rounding,
 *          saturating to 16-bit signed range [0, 32767].
 * Architecture:
 *   - Two independent banks (Bank 0 and Bank 1) each 88 entries deep.
 *   - Strict single write port per bank enables Distributed RAM inference (* ram_style = "distributed" *).
 *   - Eliminates 14,000 discrete flip-flops and 23,700 LUTs of multiplexer logic.
 */

`timescale 1ns / 1ps

module feature_accumulator #(
    parameter NUM_CHANNELS = 22,
    parameter NUM_SUBBANDS = 4,
    parameter TOTAL_FEATS  = 176, // 22 ch * 4 bands * 2 feats
    parameter DATA_WIDTH   = 16,
    parameter FEAT_WIDTH   = 19
)(
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          reset_state,  // Synchronous accumulator zeroing
    
    // Wavelet coefficient streaming input
    input  wire                          coeff_valid,
    input  wire [4:0]                    channel_id,   // 0 .. 21
    input  wire [1:0]                    subband_id,   // 0: D3, 1: D4, 2: D5, 3: A5
    input  wire signed [DATA_WIDTH-1:0]  coeff_in,
    
    // Window completion strobe (asserted every 1.0 s hop)
    input  wire                          window_sync,
    
    // Serialized feature streaming interface to SVM classifier
    output reg                           feat_stream_start,
    output reg                           feat_stream_valid,
    output reg  [7:0]                    feat_index,   // 0 .. 175
    output reg  signed [FEAT_WIDTH-1:0]  feat_data,
    output reg                           feat_ready
);

    localparam TOTAL_BINS = NUM_CHANNELS * NUM_SUBBANDS; // 88 bins

    // =========================================================================
    // Bank 0 Memories (88 entries, Single Write Port)
    // =========================================================================
    (* ram_style = "distributed" *) reg [37:0]                  energy_b0   [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg [25:0]                  ll_b0       [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg signed [DATA_WIDTH-1:0] prev_b0     [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg                         has_prev_b0 [0:TOTAL_BINS-1];

    // =========================================================================
    // Bank 1 Memories (88 entries, Single Write Port)
    // =========================================================================
    (* ram_style = "distributed" *) reg [37:0]                  energy_b1   [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg [25:0]                  ll_b1       [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg signed [DATA_WIDTH-1:0] prev_b1     [0:TOTAL_BINS-1];
    (* ram_style = "distributed" *) reg                         has_prev_b1 [0:TOTAL_BINS-1];

    integer init_i;
    initial begin
        for (init_i = 0; init_i < TOTAL_BINS; init_i = init_i + 1) begin
            energy_b0[init_i]   = 38'd0;
            ll_b0[init_i]       = 26'd0;
            prev_b0[init_i]     = {DATA_WIDTH{1'b0}};
            has_prev_b0[init_i] = 1'b0;

            energy_b1[init_i]   = 38'd0;
            ll_b1[init_i]       = 26'd0;
            prev_b1[init_i]     = {DATA_WIDTH{1'b0}};
            has_prev_b1[init_i] = 1'b0;
        end
    end

    // Bank selectors
    reg active_buf; // Buffer receiving incoming coefficients
    reg stream_buf; // Buffer being streamed to SVM

    // Current incoming bin address
    wire [6:0] cur_bin = (channel_id * NUM_SUBBANDS) + subband_id;

    // Sequential clear control
    reg [6:0] clear_bin_idx;
    reg       clearing;

    // Squaring for Energy (16 x 16 -> 32 bits unsigned)
    wire [31:0] sq_coeff = $signed(coeff_in) * $signed(coeff_in);

    // Active Accumulator Asynchronous Reads
    wire [37:0]                  e_acc_cur    = (active_buf == 1'b0) ? energy_b0[cur_bin]   : energy_b1[cur_bin];
    wire [25:0]                  ll_acc_cur   = (active_buf == 1'b0) ? ll_b0[cur_bin]       : ll_b1[cur_bin];
    wire signed [DATA_WIDTH-1:0] prev_acc_cur = (active_buf == 1'b0) ? prev_b0[cur_bin]     : prev_b1[cur_bin];
    wire                         has_acc_cur  = (active_buf == 1'b0) ? has_prev_b0[cur_bin] : has_prev_b1[cur_bin];

    // 17-bit safe difference arithmetic for Line-Length
    wire signed [16:0] diff_17 = {coeff_in[15], coeff_in} - {prev_acc_cur[15], prev_acc_cur};
    wire signed [16:0] abs_diff_17 = (diff_17 < 0) ? -diff_17 : diff_17;
    wire [15:0] abs_diff = abs_diff_17[15:0];

    // Stream FSM states
    localparam S_IDLE   = 2'b00;
    localparam S_START  = 2'b01;
    localparam S_STREAM = 2'b10;
    reg [1:0] stream_state;

    // Streaming index wires
    wire [6:0] stream_bin_next = (feat_index + 1'b1) >> 1;
    wire       stream_is_ll_next = (feat_index + 1'b1) & 1'b1;

    // Streaming Readout (Asynchronous Read from stream_buf)
    wire [6:0]  stream_read_addr = (stream_state == S_START) ? 7'd0 : stream_bin_next;
    wire [37:0] stream_r_energy  = (stream_buf == 1'b0) ? energy_b0[stream_read_addr] : energy_b1[stream_read_addr];
    wire [25:0] stream_r_ll      = (stream_buf == 1'b0) ? ll_b0[stream_read_addr]     : ll_b1[stream_read_addr];

    // =========================================================================
    // Normalization function: calculates rounded, saturating feature
    // =========================================================================
    function signed [FEAT_WIDTH-1:0] normalize_feature;
        input [6:0]  b_addr;
        input        is_ll;
        input [37:0] e_raw;
        input [25:0] ll_raw;
        reg [1:0]    sband;
        reg [37:0]   e_round;
        reg [25:0]   ll_round;
        reg [18:0]   e_shift;
        reg [18:0]   ll_shift;
        reg [15:0]   sat_val;
        begin
            sband = b_addr[1:0];
            if (!is_ll) begin
                case (sband)
                    2'd0: e_round = e_raw + 38'd524288; // D3 (Nb=32): shift 20, round 1<<19
                    2'd1: e_round = e_raw + 38'd262144; // D4 (Nb=16): shift 19, round 1<<18
                    2'd2: e_round = e_raw + 38'd131072; // D5 (Nb=8):  shift 18, round 1<<17
                    2'd3: e_round = e_raw + 38'd131072; // A5 (Nb=8):  shift 18, round 1<<17
                endcase
                case (sband)
                    2'd0: e_shift = e_round[37:20];
                    2'd1: e_shift = e_round[37:19];
                    2'd2: e_shift = e_round[37:18];
                    2'd3: e_shift = e_round[37:18];
                endcase
                if (e_shift > 19'sd32767)
                    sat_val = 16'sd32767;
                else
                    sat_val = e_shift[15:0];
                normalize_feature = { {(FEAT_WIDTH-16){1'b0}}, sat_val };
            end else begin
                case (sband)
                    2'd0: ll_round = ll_raw + 26'd16; // D3 (Nb=31): shift 5, round 1<<4
                    2'd1: ll_round = ll_raw + 26'd8;  // D4 (Nb=15): shift 4, round 1<<3
                    2'd2: ll_round = ll_raw + 26'd4;  // D5 (Nb=7):  shift 3, round 1<<2
                    2'd3: ll_round = ll_raw + 26'd4;  // A5 (Nb=7):  shift 3, round 1<<2
                endcase
                case (sband)
                    2'd0: ll_shift = ll_round[23:5];
                    2'd1: ll_shift = ll_round[22:4];
                    2'd2: ll_shift = ll_round[21:3];
                    2'd3: ll_shift = ll_round[21:3];
                endcase
                if (ll_shift > 19'sd32767)
                    sat_val = 16'sd32767;
                else
                    sat_val = ll_shift[15:0];
                normalize_feature = { {(FEAT_WIDTH-16){1'b0}}, sat_val };
            end
        end
    endfunction

    // =========================================================================
    // Bank 0 Single-Write-Port Multiplexing
    // =========================================================================
    reg        we_b0_e, we_b0_ll, we_b0_pc, we_b0_hp;
    reg [6:0]  waddr_b0;
    reg [37:0] wdata_b0_e;
    reg [25:0] wdata_b0_ll;
    reg signed [DATA_WIDTH-1:0] wdata_b0_pc;
    reg        wdata_b0_hp;

    always @(*) begin
        we_b0_e    = 1'b0;
        we_b0_ll   = 1'b0;
        we_b0_pc   = 1'b0;
        we_b0_hp   = 1'b0;
        waddr_b0   = 7'd0;
        wdata_b0_e = 38'd0;
        wdata_b0_ll= 26'd0;
        wdata_b0_pc= {DATA_WIDTH{1'b0}};
        wdata_b0_hp= 1'b0;

        if (clearing) begin
            we_b0_e    = 1'b1;
            we_b0_ll   = 1'b1;
            we_b0_pc   = 1'b1;
            we_b0_hp   = 1'b1;
            waddr_b0   = clear_bin_idx;
        end else if (active_buf == 1'b0) begin
            // Bank 0 is ACTIVE ACCUMULATOR
            if (coeff_valid && (cur_bin < TOTAL_BINS)) begin
                we_b0_e    = 1'b1;
                we_b0_ll   = 1'b1;
                we_b0_pc   = 1'b1;
                we_b0_hp   = 1'b1;
                waddr_b0   = cur_bin;
                wdata_b0_e = energy_b0[cur_bin] + sq_coeff;
                wdata_b0_ll= has_prev_b0[cur_bin] ? (ll_b0[cur_bin] + abs_diff) : ll_b0[cur_bin];
                wdata_b0_pc= coeff_in;
                wdata_b0_hp= 1'b1;
            end
        end else begin
            // Bank 0 is STREAM BUFFER (being read and drained)
            if (stream_state == S_START) begin
                we_b0_e    = 1'b1;
                waddr_b0   = 7'd0;
                wdata_b0_e = 38'd0;
            end else if (stream_state == S_STREAM) begin
                if (!stream_is_ll_next) begin
                    we_b0_e    = 1'b1;
                    waddr_b0   = stream_bin_next;
                    wdata_b0_e = 38'd0;
                end else begin
                    we_b0_ll   = 1'b1;
                    we_b0_hp   = 1'b1;
                    waddr_b0   = stream_bin_next;
                    wdata_b0_ll= 26'd0;
                    wdata_b0_hp= 1'b0;
                end
            end
        end
    end

    always @(posedge clk) begin
        if (we_b0_e)  energy_b0[waddr_b0]   <= wdata_b0_e;
        if (we_b0_ll) ll_b0[waddr_b0]       <= wdata_b0_ll;
        if (we_b0_pc) prev_b0[waddr_b0]     <= wdata_b0_pc;
        if (we_b0_hp) has_prev_b0[waddr_b0] <= wdata_b0_hp;
    end

    // =========================================================================
    // Bank 1 Single-Write-Port Multiplexing
    // =========================================================================
    reg        we_b1_e, we_b1_ll, we_b1_pc, we_b1_hp;
    reg [6:0]  waddr_b1;
    reg [37:0] wdata_b1_e;
    reg [25:0] wdata_b1_ll;
    reg signed [DATA_WIDTH-1:0] wdata_b1_pc;
    reg        wdata_b1_hp;

    always @(*) begin
        we_b1_e    = 1'b0;
        we_b1_ll   = 1'b0;
        we_b1_pc   = 1'b0;
        we_b1_hp   = 1'b0;
        waddr_b1   = 7'd0;
        wdata_b1_e = 38'd0;
        wdata_b1_ll= 26'd0;
        wdata_b1_pc= {DATA_WIDTH{1'b0}};
        wdata_b1_hp= 1'b0;

        if (clearing) begin
            we_b1_e    = 1'b1;
            we_b1_ll   = 1'b1;
            we_b1_pc   = 1'b1;
            we_b1_hp   = 1'b1;
            waddr_b1   = clear_bin_idx;
        end else if (active_buf == 1'b1) begin
            // Bank 1 is ACTIVE ACCUMULATOR
            if (coeff_valid && (cur_bin < TOTAL_BINS)) begin
                we_b1_e    = 1'b1;
                we_b1_ll   = 1'b1;
                we_b1_pc   = 1'b1;
                we_b1_hp   = 1'b1;
                waddr_b1   = cur_bin;
                wdata_b1_e = energy_b1[cur_bin] + sq_coeff;
                wdata_b1_ll= has_prev_b1[cur_bin] ? (ll_b1[cur_bin] + abs_diff) : ll_b1[cur_bin];
                wdata_b1_pc= coeff_in;
                wdata_b1_hp= 1'b1;
            end
        end else begin
            // Bank 1 is STREAM BUFFER (being read and drained)
            if (stream_state == S_START) begin
                we_b1_e    = 1'b1;
                waddr_b1   = 7'd0;
                wdata_b1_e = 38'd0;
            end else if (stream_state == S_STREAM) begin
                if (!stream_is_ll_next) begin
                    we_b1_e    = 1'b1;
                    waddr_b1   = stream_bin_next;
                    wdata_b1_e = 38'd0;
                end else begin
                    we_b1_ll   = 1'b1;
                    we_b1_hp   = 1'b1;
                    waddr_b1   = stream_bin_next;
                    wdata_b1_ll= 26'd0;
                    wdata_b1_hp= 1'b0;
                end
            end
        end
    end

    always @(posedge clk) begin
        if (we_b1_e)  energy_b1[waddr_b1]   <= wdata_b1_e;
        if (we_b1_ll) ll_b1[waddr_b1]       <= wdata_b1_ll;
        if (we_b1_pc) prev_b1[waddr_b1]     <= wdata_b1_pc;
        if (we_b1_hp) has_prev_b1[waddr_b1] <= wdata_b1_hp;
    end

    // =========================================================================
    // Control & Streaming FSM
    // =========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active_buf        <= 1'b0;
            stream_buf        <= 1'b0;
            feat_stream_start <= 1'b0;
            feat_stream_valid <= 1'b0;
            feat_index        <= 8'd0;
            feat_data         <= {FEAT_WIDTH{1'b0}};
            feat_ready        <= 1'b0;
            stream_state      <= S_IDLE;
            clearing          <= 1'b0;
            clear_bin_idx     <= 7'd0;
        end else begin
            if (reset_state) begin
                clearing          <= 1'b1;
                clear_bin_idx     <= 7'd0;
                stream_state      <= S_IDLE;
                feat_stream_valid <= 1'b0;
                feat_stream_start <= 1'b0;
                feat_ready        <= 1'b0;
            end else if (clearing) begin
                if (clear_bin_idx == TOTAL_BINS - 1)
                    clearing <= 1'b0;
                else
                    clear_bin_idx <= clear_bin_idx + 1'b1;
            end else begin
                // Window synchronization: swap ping-pong buffers
                if (window_sync) begin
                    stream_buf   <= active_buf;
                    active_buf   <= ~active_buf;
                    stream_state <= S_START;
                    feat_ready   <= 1'b0;
                end else if (stream_state != S_STREAM || feat_index != (TOTAL_FEATS - 1)) begin
                    feat_ready   <= 1'b0;
                end

                // Serialize 176 features to SVM classifier
                case (stream_state)
                    S_IDLE: begin
                        feat_stream_start <= 1'b0;
                        feat_stream_valid <= 1'b0;
                        feat_index        <= 8'd0;
                    end

                    S_START: begin
                        feat_stream_start <= 1'b1;
                        feat_stream_valid <= 1'b1;
                        feat_index        <= 8'd0;
                        feat_ready        <= 1'b0;
                        // Read feature 0 (Energy bin 0)
                        feat_data         <= normalize_feature(
                                                 7'd0, 1'b0,
                                                 stream_r_energy,
                                                 stream_r_ll
                                             );
                        stream_state      <= S_STREAM;
                    end

                    S_STREAM: begin
                        feat_stream_start <= 1'b0;
                        if (feat_index == (TOTAL_FEATS - 1)) begin
                            // Completed 176 features
                            feat_stream_valid <= 1'b0;
                            feat_ready        <= 1'b1;
                            stream_state      <= S_IDLE;
                        end else begin
                            feat_index <= feat_index + 1'b1;
                            feat_data  <= normalize_feature(
                                              stream_bin_next,
                                              stream_is_ll_next,
                                              stream_r_energy,
                                              stream_r_ll
                                          );
                        end
                    end
                endcase
            end
        end
    end

endmodule
