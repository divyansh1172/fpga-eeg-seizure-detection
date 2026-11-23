/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Team: 15
 * Author: Member 4 (Vivado Implementation Lead) & Member 3 (RTL Datapath Lead)
 * Purpose: Top-level synthesizable FPGA Seizure Detection System on RealDigital Boolean Board.
 *          Integrates UART RX -> IIR Biquad -> db4 DWT -> Feature Accumulator -> Linear SVM
 *          -> Alarm Logic -> 7-Segment Display, RGB LED, and Board LEDs.
 * Target: AMD Spartan-7 XC7S50 (xc7s50csga324-1) at 100 MHz clock.
 * AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Member 4)
 */

`timescale 1ns / 1ps

module top_seizure_detector #(
    parameter CLK_FREQ_HZ   = 100000000,
    parameter BAUD_RATE     = 230400,
    parameter NUM_CHANNELS  = 22,
    parameter NUM_SUBBANDS  = 4,
    parameter TOTAL_FEATS   = 176,
    parameter DATA_WIDTH    = 16
)(
    input  wire        clk,          // 100 MHz onboard clock (Pin F14)
    input  wire        rst,          // Active-high synchronous reset button BTN0 (Pin J2)
    input  wire [3:1]  btn,          // Pushbuttons BTN1..BTN3
    
    // USB-UART Bridge interface
    input  wire        uart_rxd,     // RXD serial data from PC (Pin V15)
    output wire        uart_txd,     // TXD serial telemetry to PC (Pin W15)
    
    // Slide switches
    input  wire [15:0] sw,           // sw[1:0] configure alarm persistence k (1, 2, 3, 5)
    
    // Discrete LEDs
    output reg  [15:0] led,          // led[15]: Alarm strobe, led[14:13]: consec count, led[4:0]: ch
    
    // RGB Status LED 0
    output reg         rgb0_r,       // Red (Alarm indicator, Pin V6)
    output reg         rgb0_g,       // Green (Streaming OK indicator, Pin U6)
    output reg         rgb0_b,       // Blue (Pin U7)
    
    // Dual 4-digit 7-segment display (8 digits total)
    output wire [7:0]  anode,        // Active-low digit enables
    output wire [6:0]  seg,          // Active-low cathode segments A..G (Display 0)
    output wire        dp,           // Active-low decimal point (Display 0)
    output wire [6:0]  seg1,         // Active-low cathode segments A..G (Display 1)
    output wire        dp1           // Active-low decimal point (Display 1)
);

    // 2-Flop Reset Synchronizer (Async Assert, Sync Deassert)
    reg [1:0] rst_sync;
    always @(posedge clk or posedge rst) begin
        if (rst)
            rst_sync <= 2'b00;
        else
            rst_sync <= {rst_sync[0], 1'b1};
    end
    wire rst_n = rst_sync[1];

    // Synchronous 1-cycle pulse upon rst_n release to trigger sequential memory clearing
    reg rst_n_d;
    reg post_rst_clear;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst_n_d        <= 1'b0;
            post_rst_clear <= 1'b0;
        end else begin
            rst_n_d        <= 1'b1;
            post_rst_clear <= !rst_n_d;
        end
    end

    // 2-Flop Synchronizer for btn[1] (Alarm Clear Button)
    reg [1:0] btn1_sync;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            btn1_sync <= 2'b00;
        else
            btn1_sync <= {btn1_sync[0], btn[1]};
    end
    wire btn_clear_sync = btn1_sync[1];

    // =========================================================================
    // 1. UART Receiver & Packet Decoder
    // Protocol: 4 bytes per sample (0xAA, channel_id, MSB, LSB)
    // =========================================================================
    wire       byte_valid;
    wire [7:0] byte_data;
    wire       frame_err;

    uart_rx #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ),
        .BAUD_RATE(BAUD_RATE)
    ) u_uart_rx (
        .clk(clk),
        .rst_n(rst_n),
        .rxd(uart_rxd),
        .byte_valid(byte_valid),
        .byte_data(byte_data),
        .frame_err(frame_err)
    );

    // Packet framing state machine
    reg [1:0] pkt_state;
    localparam PKT_SYNC = 2'd0;
    localparam PKT_CHAN = 2'd1;
    localparam PKT_MSB  = 2'd2;
    localparam PKT_LSB  = 2'd3;

    reg [4:0]                   curr_ch;
    reg [7:0]                   sample_msb;
    reg signed [DATA_WIDTH-1:0] sample_in;
    reg                         sample_valid;

    // Diagnostic & error monitoring counters
    reg [15:0] frame_err_count;
    reg [15:0] dropped_frame_count;
    reg [15:0] sync_err_count;

    // Sample and window pacing counters
    reg [8:0]  ch_sample_counter; // 0..255 frames per 1-second hop (fs=256 Hz)
    reg [15:0] playback_seconds;
    reg        hop_sync;
    reg [7:0]  hop_drain_cnt;
    reg        hop_drain_active;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pkt_state           <= PKT_SYNC;
            curr_ch             <= 5'd0;
            sample_msb          <= 8'd0;
            sample_in           <= {DATA_WIDTH{1'b0}};
            sample_valid        <= 1'b0;
            ch_sample_counter   <= 9'd0;
            playback_seconds    <= 16'd0;
            hop_sync            <= 1'b0;
            hop_drain_cnt       <= 8'd0;
            hop_drain_active    <= 1'b0;
            frame_err_count     <= 16'd0;
            dropped_frame_count <= 16'd0;
            sync_err_count      <= 16'd0;
        end else begin
            sample_valid <= 1'b0;

            // Track physical UART framing errors
            if (frame_err) begin
                frame_err_count <= frame_err_count + 1'b1;
                pkt_state       <= PKT_SYNC; // Abort in-flight frame on framing error
            end

            if (byte_valid) begin
                case (pkt_state)
                    PKT_SYNC: begin
                        if (byte_data == 8'hAA) begin
                            pkt_state <= PKT_CHAN;
                        end else begin
                            sync_err_count <= sync_err_count + 1'b1;
                        end
                    end

                    PKT_CHAN: begin
                        if (byte_data < NUM_CHANNELS) begin
                            curr_ch   <= byte_data[4:0];
                            pkt_state <= PKT_MSB;
                        end else if (byte_data == 8'hAA) begin
                            // Robust resync heuristic: previous frame truncated, this is new header
                            pkt_state           <= PKT_CHAN;
                            dropped_frame_count <= dropped_frame_count + 1'b1;
                        end else begin
                            // Invalid channel ID: drop and return to sync search
                            pkt_state           <= PKT_SYNC;
                            dropped_frame_count <= dropped_frame_count + 1'b1;
                        end
                    end

                    PKT_MSB: begin
                        sample_msb <= byte_data;
                        pkt_state  <= PKT_LSB;
                    end

                    PKT_LSB: begin
                        sample_in    <= {sample_msb, byte_data};
                        sample_valid <= 1'b1;
                        pkt_state    <= PKT_SYNC;

                        // Increment frame counter on last channel (ch 21)
                        if (curr_ch == NUM_CHANNELS - 1) begin
                            if (ch_sample_counter == 9'd255) begin
                                ch_sample_counter <= 9'd0;
                                playback_seconds  <= playback_seconds + 1'b1;
                                hop_drain_active  <= 1'b1; // Start drain counter for pipeline flush
                                hop_drain_cnt     <= 8'd0;
                            end else begin
                                ch_sample_counter <= ch_sample_counter + 1'b1;
                            end
                        end
                    end
                endcase
            end

            // Pipeline flush timer: assert hop_sync 128 cycles after last sample.
            // Guarantees all 5 cascaded serial DWT stages (45 cyc) and FIFO drain (8 cyc)
            // have completely finished before swapping ping-pong banks.
            if (hop_drain_active) begin
                if (hop_drain_cnt == 8'd128) begin
                    hop_drain_active <= 1'b0;
                    hop_sync         <= 1'b1;
                end else begin
                    hop_drain_cnt <= hop_drain_cnt + 1'b1;
                    hop_sync      <= 1'b0;
                end
            end else begin
                hop_sync <= 1'b0;
            end
        end
    end

    // =========================================================================
    // 2. Front-End Causal IIR Bandpass Filter (0.5 - 25 Hz)
    // =========================================================================
    wire                          iir_out_valid;
    wire [4:0]                    iir_ch_out;
    wire signed [DATA_WIDTH-1:0]  iir_sample_out;

    iir_biquad #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_iir_biquad (
        .clk(clk),
        .rst_n(rst_n),
        .reset_state(post_rst_clear),
        .sample_valid(sample_valid),
        .ch_in(curr_ch),
        .sample_in(sample_in),
        .out_valid(iir_out_valid),
        .ch_out(iir_ch_out),
        .sample_out(iir_sample_out)
    );

    // =========================================================================
    // 3. 5-Level Daubechies-4 DWT Analysis Filter Bank
    // =========================================================================
    wire                          dwt_valid;
    wire [4:0]                    dwt_ch_out;
    wire [1:0]                    dwt_subband_id;
    wire signed [DATA_WIDTH-1:0]  dwt_coeff_out;
    wire                          dwt_valid_d3;
    wire                          dwt_valid_d4;
    wire                          dwt_valid_d5;
    wire                          dwt_valid_a5;
    wire signed [DATA_WIDTH-1:0]  dwt_approx;
    wire signed [DATA_WIDTH-1:0]  dwt_detail;

    dwt_db4 #(
        .DATA_WIDTH(DATA_WIDTH),
        .NUM_CHANNELS(NUM_CHANNELS)
    ) u_dwt_db4 (
        .clk(clk),
        .rst_n(rst_n),
        .sample_valid(iir_out_valid),
        .ch_in(iir_ch_out),
        .sample_in(iir_sample_out),
        .out_valid(dwt_valid),
        .ch_out(dwt_ch_out),
        .subband_id(dwt_subband_id),
        .coeff_out(dwt_coeff_out),
        .valid_d3(dwt_valid_d3),
        .valid_d4(dwt_valid_d4),
        .valid_d5(dwt_valid_d5),
        .valid_a5(dwt_valid_a5),
        .approx_out(dwt_approx),
        .detail_out(dwt_detail)
    );

    // =========================================================================
    // 4. Feature Accumulators with Dynamic Wire-Shift (Energy & Line-Length)
    // =========================================================================
    wire         feat_stream_start;
    wire         feat_stream_valid;
    wire [7:0]   feat_index;
    wire signed [18:0] feat_data_raw;
    wire         feat_ready;

    feature_accumulator #(
        .NUM_CHANNELS(NUM_CHANNELS),
        .NUM_SUBBANDS(NUM_SUBBANDS),
        .TOTAL_FEATS(TOTAL_FEATS),
        .DATA_WIDTH(DATA_WIDTH),
        .FEAT_WIDTH(19)
    ) u_feature_accumulator (
        .clk(clk),
        .rst_n(rst_n),
        .reset_state(post_rst_clear),
        .coeff_valid(dwt_valid),
        .channel_id(dwt_ch_out),
        .subband_id(dwt_subband_id),
        .coeff_in(dwt_coeff_out),
        .window_sync(hop_sync),
        .feat_stream_start(feat_stream_start),
        .feat_stream_valid(feat_stream_valid),
        .feat_index(feat_index),
        .feat_data(feat_data_raw),
        .feat_ready(feat_ready)
    );

    // Truncate/saturate 19-bit normalized feature to 16-bit for SVM multiplier
    wire signed [15:0] feat_data_16 = (feat_data_raw > 19'sd32767) ? 16'sh7FFF :
                                      (feat_data_raw < -19'sd32768) ? 16'sh8000 :
                                      feat_data_raw[15:0];

    // =========================================================================
    // 5. Offline Folded Linear SVM Weight ROM & Classifier
    // Evaluates: y = sum(w_eff * X) + b_eff in 176 clock cycles
    // =========================================================================
    reg signed [15:0] svm_weight_rom [0:TOTAL_FEATS-1];
    localparam signed [31:0] SVM_BIAS_EFF = 32'shFFF43986; // Exact 32-bit offline folded bias (-771706)

    initial begin
        $readmemh("weights.mem", svm_weight_rom);
    end

    wire signed [15:0] current_weight = svm_weight_rom[feat_index];

    wire svm_done;
    wire svm_decision;
    wire signed [39:0] svm_score;

    svm_classifier #(
        .FEAT_DIM(TOTAL_FEATS),
        .FEAT_WIDTH(16),
        .WEIGHT_WIDTH(16),
        .BIAS_WIDTH(32),
        .ACCUM_WIDTH(40)
    ) u_svm_classifier (
        .clk(clk),
        .rst_n(rst_n),
        .start(feat_stream_start),
        .feat_data(feat_data_16),
        .weight_data(current_weight),
        .bias_data(SVM_BIAS_EFF),
        .done(svm_done),
        .decision(svm_decision),
        .score(svm_score)
    );

    // =========================================================================
    // 6. Alarm Post-Processing, Refractory Logic & Telemetry
    // sw[1:0] selects persistence k: 00 -> k=1, 01 -> k=2, 10 -> k=3, 11 -> k=5
    // btn[1] manually clears latched alarm
    // =========================================================================
    wire        alarm_pulse;
    wire        seizure_alarm_latched;
    wire [7:0]  alarm_counter;
    wire [2:0]  consec_pos_count;
    wire        refractory_active;
    wire [5:0]  refractory_sec_timer;
    wire [15:0] latched_latency;
    wire        tx_trigger;

    alarm_logic u_alarm_logic (
        .clk(clk),
        .rst_n(rst_n),
        .k_sel(sw[1:0]),
        .btn_clear(btn_clear_sync),
        .svm_done(svm_done),
        .svm_decision(svm_decision),
        .sec_tick(hop_sync),
        .playback_seconds(playback_seconds),
        .alarm_pulse(alarm_pulse),
        .alarm_latched(seizure_alarm_latched),
        .alarm_count(alarm_counter),
        .consec_count(consec_pos_count),
        .refractory_active(refractory_active),
        .refractory_timer(refractory_sec_timer),
        .latched_latency(latched_latency),
        .tx_trigger(tx_trigger)
    );

    // Telemetry UART Transmitter (230,400 baud)
    wire tx_busy;
    uart_tx #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ),
        .BAUD_RATE(BAUD_RATE)
    ) u_uart_tx (
        .clk(clk),
        .rst_n(rst_n),
        .tx_start(tx_trigger),
        .tx_data(8'hA5), // Alarm Alert telemetry byte
        .tx_busy(tx_busy),
        .txd(uart_txd)
    );

    // =========================================================================
    // 7. Visual Indicators & 7-Segment Controller
    // =========================================================================
    // Strobe generator for LED15 alarm strobe (~6 Hz)
    reg [23:0] strobe_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            strobe_cnt <= 24'd0;
        else
            strobe_cnt <= strobe_cnt + 1'b1;
    end
    wire alarm_strobe = strobe_cnt[23];

    // Discrete LEDs mapping
    always @(*) begin
        led[4:0]   = curr_ch;                      // led[4:0]: Active channel index
        led[12:5]  = 8'd0;
        led[13]    = (consec_pos_count >= 3'd1);   // Consecutive window 1
        led[14]    = (consec_pos_count >= 3'd2);   // Consecutive window 2
        led[15]    = seizure_alarm_latched ? alarm_strobe : 1'b0; // Seizure Alarm strobe
    end

    // Streaming watchdog: asserts streaming_ok if samples arrived within the last 1.0 s
    reg [26:0] stream_watchdog;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            stream_watchdog <= 27'd0;
        else if (sample_valid)
            stream_watchdog <= 27'd100000000; // 1.0 second re-trigger
        else if (stream_watchdog > 27'd0)
            stream_watchdog <= stream_watchdog - 1'b1;
    end
    wire streaming_ok = (stream_watchdog > 27'd0);

    // RGB Status LED 0: Solid Green during active streaming, Flashing Red on seizure
    always @(*) begin
        if (seizure_alarm_latched) begin
            rgb0_r = alarm_strobe; // Flashing Red on seizure
            rgb0_g = 1'b0;
            rgb0_b = 1'b0;
        end else begin
            rgb0_r = 1'b0;
            rgb0_g = streaming_ok; // Solid Green when streaming is active
            rgb0_b = 1'b0;
        end
    end

    // 8-Digit Common-Anode 7-Segment Display Controller
    seven_seg_controller #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ),
        .REFRESH_HZ(1000)
    ) u_seven_seg_controller (
        .clk(clk),
        .rst_n(rst_n),
        .playback_time(playback_seconds),
        .latency(latched_latency),
        .alarm_active(seizure_alarm_latched),
        .alarm_count(alarm_counter),
        .anode(anode),
        .seg(seg),
        .dp(dp),
        .seg1(seg1),
        .dp1(dp1)
    );

endmodule
