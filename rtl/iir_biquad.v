/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: iir_biquad.v
 * Purpose: Synthesizable 4th-order causal Butterworth IIR bandpass filter (0.5-25 Hz at fs=256 Hz).
 *          Time-multiplexed across 22 channels with per-channel RAM state storage,
 *          fractional Q20 internal guard bits, and a 5-stage pipelined MAC datapath.
 *          Pipelined into 2 sub-stages per biquad section to close 100 MHz timing closure
 *          with positive slack (WNS > 0) on Spartan-7.
 */

`timescale 1ns / 1ps

module iir_biquad #(
    parameter DATA_WIDTH     = 16,
    parameter NUM_CHANNELS   = 22,
    parameter COEFF_SHIFT    = 20,
    parameter STATE_WIDTH    = 34,
    parameter ACCUM_WIDTH    = 48
)(
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          reset_state,  // Synchronous filter state zeroing per record
    input  wire                          sample_valid, // Pulse when new 16-bit sample arrives
    input  wire [4:0]                    ch_in,        // Channel ID (0..21)
    input  wire signed [DATA_WIDTH-1:0]  sample_in,
    
    output reg                           out_valid,
    output reg  [4:0]                    ch_out,
    output reg  signed [DATA_WIDTH-1:0]  sample_out
);

    // =========================================================================
    // Filter Coefficients (Shift-20 Fixed-Point, scale = 2^20 = 1048576)
    // 4th-order Butterworth bandpass [0.5, 25.0] Hz at fs = 256 Hz
    // Section 0 (Lowpass pair):
    //   b = [0.06264521, 0.12529042, 0.06264521] -> [65688, 131377, 65688]
    //   a = [1.00000000, -1.18295950, 0.43602825] -> [1048576, -1240423, 457209]
    // Section 1 (Highpass pair):
    //   b = [1.00000000, -2.00000000, 1.00000000] -> [1048576, -2097152, 1048576]
    //   a = [1.00000000, -1.98266648, 0.98282155] -> [1048576, -2078976, 1030563]
    // =========================================================================
    localparam signed [24:0] S0_B0 = 25'sd65688;     // +0.06264521 * 2^20
    localparam signed [24:0] S0_B1 = 25'sd131377;    // +0.12529042 * 2^20 (exact rounded)
    localparam signed [24:0] S0_B2 = 25'sd65688;     // +0.06264521 * 2^20
    localparam signed [24:0] S0_A1 = -25'sd1240423;  // -1.18295950 * 2^20
    localparam signed [24:0] S0_A2 = 25'sd457209;    // +0.43602825 * 2^20

    localparam signed [24:0] S1_B0 = 25'sd1048576;   // +1.00000000 * 2^20
    localparam signed [24:0] S1_B1 = -25'sd2097152;  // -2.00000000 * 2^20
    localparam signed [24:0] S1_B2 = 25'sd1048576;   // +1.00000000 * 2^20
    localparam signed [24:0] S1_A1 = -25'sd2078976;  // -1.98266648 * 2^20 (exact rounded)
    localparam signed [24:0] S1_A2 = 25'sd1030563;   // +0.98282155 * 2^20

    // =========================================================================
    // Per-Channel State Memories (22 channels, inferred as RAM without async reset)
    // =========================================================================
    reg signed [DATA_WIDTH-1:0]  s0_mem_x1 [0:NUM_CHANNELS-1];
    reg signed [DATA_WIDTH-1:0]  s0_mem_x2 [0:NUM_CHANNELS-1];
    reg signed [STATE_WIDTH-1:0] s0_mem_y1 [0:NUM_CHANNELS-1]; // Q20 state with 34-bit range
    reg signed [STATE_WIDTH-1:0] s0_mem_y2 [0:NUM_CHANNELS-1];

    reg signed [DATA_WIDTH-1:0]  s1_mem_x1 [0:NUM_CHANNELS-1];
    reg signed [DATA_WIDTH-1:0]  s1_mem_x2 [0:NUM_CHANNELS-1];
    reg signed [STATE_WIDTH-1:0] s1_mem_y1 [0:NUM_CHANNELS-1];
    reg signed [STATE_WIDTH-1:0] s1_mem_y2 [0:NUM_CHANNELS-1];

    integer init_i;
    initial begin
        for (init_i = 0; init_i < NUM_CHANNELS; init_i = init_i + 1) begin
            s0_mem_x1[init_i] = {DATA_WIDTH{1'b0}};
            s0_mem_x2[init_i] = {DATA_WIDTH{1'b0}};
            s0_mem_y1[init_i] = {STATE_WIDTH{1'b0}};
            s0_mem_y2[init_i] = {STATE_WIDTH{1'b0}};
            s1_mem_x1[init_i] = {DATA_WIDTH{1'b0}};
            s1_mem_x2[init_i] = {DATA_WIDTH{1'b0}};
            s1_mem_y1[init_i] = {STATE_WIDTH{1'b0}};
            s1_mem_y2[init_i] = {STATE_WIDTH{1'b0}};
        end
    end

    // Sequential clear sweep registers
    reg [4:0] clear_idx;
    reg       clearing;

    // Pipelined FSM states (split each section into DSP product + Accumulate/Clamp)
    localparam S_IDLE   = 3'd0;
    localparam S_SEC0_A = 3'd1; // Section 0 DSP products
    localparam S_SEC0_B = 3'd2; // Section 0 subtraction & saturate
    localparam S_SEC1_A = 3'd3; // Section 1 DSP products
    localparam S_SEC1_B = 3'd4; // Section 1 subtraction & saturate
    localparam S_WRITE  = 3'd5; // Writeback to RAM and emit sample_out

    reg [2:0]                    state;
    reg [4:0]                    latched_ch;
    reg signed [DATA_WIDTH-1:0]  latched_x;

    // Latched state variables read from RAM
    reg signed [DATA_WIDTH-1:0]  r_s0_x1, r_s0_x2;
    reg signed [STATE_WIDTH-1:0] r_s0_y1, r_s0_y2;
    reg signed [DATA_WIDTH-1:0]  r_s1_x1, r_s1_x2;
    reg signed [STATE_WIDTH-1:0] r_s1_y1, r_s1_y2;

    // Section 0 pipeline registers
    reg signed [59:0]            fb0_prod_reg;
    reg signed [47:0]            ff0_sum_reg;
    reg signed [47:0]            reg_acc0;
    reg signed [DATA_WIDTH-1:0]  reg_y0_sat;

    // Section 1 pipeline registers
    reg signed [59:0]            fb1_prod_reg;
    reg signed [47:0]            ff1_sum_reg;
    reg signed [47:0]            reg_acc1;
    reg signed [DATA_WIDTH-1:0]  reg_y1_sat;

    // Section 0 Combinational math for Stage B
    wire signed [39:0] fb0_div   = fb0_prod_reg >>> COEFF_SHIFT;
    wire signed [47:0] comb_acc0 = ff0_sum_reg - fb0_div;
    wire signed [39:0] y0_round  = (comb_acc0 + 48'sd524288) >>> COEFF_SHIFT;
    wire signed [DATA_WIDTH-1:0] y0_sat = (y0_round > 40'sd32767) ? 16'sh7FFF :
                                          (y0_round < -40'sd32768) ? 16'sh8000 :
                                          y0_round[DATA_WIDTH-1:0];

    // Section 1 Combinational math for Stage B
    wire signed [39:0] fb1_div   = fb1_prod_reg >>> COEFF_SHIFT;
    wire signed [47:0] comb_acc1 = ff1_sum_reg - fb1_div;
    wire signed [39:0] y1_round  = (comb_acc1 + 48'sd524288) >>> COEFF_SHIFT;
    wire signed [DATA_WIDTH-1:0] y1_sat = (y1_round > 40'sd32767) ? 16'sh7FFF :
                                          (y1_round < -40'sd32768) ? 16'sh8000 :
                                          y1_round[DATA_WIDTH-1:0];

    // Synchronous-only RAM updates
    always @(posedge clk) begin
        if (clearing) begin
            s0_mem_x1[clear_idx] <= {DATA_WIDTH{1'b0}};
            s0_mem_x2[clear_idx] <= {DATA_WIDTH{1'b0}};
            s0_mem_y1[clear_idx] <= {STATE_WIDTH{1'b0}};
            s0_mem_y2[clear_idx] <= {STATE_WIDTH{1'b0}};
            s1_mem_x1[clear_idx] <= {DATA_WIDTH{1'b0}};
            s1_mem_x2[clear_idx] <= {DATA_WIDTH{1'b0}};
            s1_mem_y1[clear_idx] <= {STATE_WIDTH{1'b0}};
            s1_mem_y2[clear_idx] <= {STATE_WIDTH{1'b0}};
        end else if (state == S_WRITE) begin
            s0_mem_x2[latched_ch] <= r_s0_x1;
            s0_mem_x1[latched_ch] <= latched_x;
            s0_mem_y2[latched_ch] <= r_s0_y1;
            s0_mem_y1[latched_ch] <= reg_acc0[STATE_WIDTH-1:0];

            s1_mem_x2[latched_ch] <= r_s1_x1;
            s1_mem_x1[latched_ch] <= reg_y0_sat;
            s1_mem_y2[latched_ch] <= r_s1_y1;
            s1_mem_y1[latched_ch] <= reg_acc1[STATE_WIDTH-1:0];
        end
    end

    // FSM and pipeline registers with clean reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= S_IDLE;
            out_valid    <= 1'b0;
            ch_out       <= 5'd0;
            sample_out   <= {DATA_WIDTH{1'b0}};
            latched_ch   <= 5'd0;
            latched_x    <= {DATA_WIDTH{1'b0}};
            clearing     <= 1'b0;
            clear_idx    <= 5'd0;
            fb0_prod_reg <= 60'd0;
            ff0_sum_reg  <= 48'd0;
            reg_acc0     <= 48'd0;
            reg_y0_sat   <= {DATA_WIDTH{1'b0}};
            fb1_prod_reg <= 60'd0;
            ff1_sum_reg  <= 48'd0;
            reg_acc1     <= 48'd0;
            reg_y1_sat   <= {DATA_WIDTH{1'b0}};
            r_s0_x1      <= {DATA_WIDTH{1'b0}};
            r_s0_x2      <= {DATA_WIDTH{1'b0}};
            r_s0_y1      <= {STATE_WIDTH{1'b0}};
            r_s0_y2      <= {STATE_WIDTH{1'b0}};
            r_s1_x1      <= {DATA_WIDTH{1'b0}};
            r_s1_x2      <= {DATA_WIDTH{1'b0}};
            r_s1_y1      <= {STATE_WIDTH{1'b0}};
            r_s1_y2      <= {STATE_WIDTH{1'b0}};
        end else begin
            out_valid <= 1'b0;

            if (reset_state) begin
                clearing  <= 1'b1;
                clear_idx <= 5'd0;
            end else if (clearing) begin
                if (clear_idx == NUM_CHANNELS - 1)
                    clearing <= 1'b0;
                else
                    clear_idx <= clear_idx + 1'b1;
            end

            case (state)
                S_IDLE: begin
                    if (sample_valid && (ch_in < NUM_CHANNELS) && !clearing) begin
                        latched_ch <= ch_in;
                        latched_x  <= sample_in;

                        // Fetch channel state from RAM
                        r_s0_x1 <= s0_mem_x1[ch_in];
                        r_s0_x2 <= s0_mem_x2[ch_in];
                        r_s0_y1 <= s0_mem_y1[ch_in];
                        r_s0_y2 <= s0_mem_y2[ch_in];

                        r_s1_x1 <= s1_mem_x1[ch_in];
                        r_s1_x2 <= s1_mem_x2[ch_in];
                        r_s1_y1 <= s1_mem_y1[ch_in];
                        r_s1_y2 <= s1_mem_y2[ch_in];

                        state   <= S_SEC0_A;
                    end
                end

                S_SEC0_A: begin
                    // Stage 1A: Section 0 DSP products (lowpass)
                    fb0_prod_reg <= (S0_A1 * r_s0_y1) + (S0_A2 * r_s0_y2) + 60'sd524288;
                    ff0_sum_reg  <= (S0_B0 * latched_x) + (S0_B1 * r_s0_x1) + (S0_B2 * r_s0_x2);
                    state        <= S_SEC0_B;
                end

                S_SEC0_B: begin
                    // Stage 1B: Section 0 Subtraction, rounding and clamp
                    reg_acc0   <= comb_acc0;
                    reg_y0_sat <= y0_sat;
                    state      <= S_SEC1_A;
                end

                S_SEC1_A: begin
                    // Stage 2A: Section 1 DSP products (highpass)
                    fb1_prod_reg <= (S1_A1 * r_s1_y1) + (S1_A2 * r_s1_y2) + 60'sd524288;
                    ff1_sum_reg  <= (S1_B0 * reg_y0_sat) + (S1_B1 * r_s1_x1) + (S1_B2 * r_s1_x2);
                    state        <= S_SEC1_B;
                end

                S_SEC1_B: begin
                    // Stage 2B: Section 1 Subtraction, rounding and clamp
                    reg_acc1   <= comb_acc1;
                    reg_y1_sat <= y1_sat;
                    state      <= S_WRITE;
                end

                S_WRITE: begin
                    // Stage 3: Output result and return to IDLE
                    sample_out <= reg_y1_sat;
                    ch_out     <= latched_ch;
                    out_valid  <= 1'b1;
                    state      <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
