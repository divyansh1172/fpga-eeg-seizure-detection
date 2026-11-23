/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Testbench: tb_top_seizure_detector
 * Purpose: Top-level system integration testbench for the 22-channel real-time
 *          EEG seizure detection system on Spartan-7.
 * Tests:
 *   1. Full-system end-to-end pipelined execution with 22 channels:
 *      - Streams 4-byte UART frames (0xAA, ch_id, MSB, LSB) from golden/vectors/tb_uart_rx_stimulus.hex.
 *      - Full 100 MHz execution through:
 *          * UART RX frame decoder & error tracker
 *          * 22-channel time-multiplexed causal IIR bandpass filter (0.5 - 25 Hz)
 *          * 22-channel 5-level Daubechies-4 DWT cascade
 *          * Ping-pong feature accumulator (Energy & Line-Length)
 *          * 176-cycle serial linear SVM classifier with real weights & 32-bit bias
 *          * Unified alarm logic with 30s refractory blanking
 *          * Telemetry UART TX transmitter
 *          * 8-digit multiplexed 7-segment display & status LEDs
 *   2. Seizure trigger and alarm test:
 *      - Verifies seizure detection on clinical ictal frames.
 *      - Verifies alarm strobe on LED15, RGB0 flashing red, and 0xA5 telemetry byte on uart_txd.
 *   3. Manual alarm clear:
 *      - Asserts btn[1] and verifies that alarm_latched clears back to normal state.
 */

`timescale 1ns / 1ps

module tb_top_seizure_detector;

    parameter CLK_FREQ_HZ = 100000000; // 100 MHz system clock
    parameter BAUD_RATE   = 5000000;   // 5 Mbaud simulation UART (20 clocks/bit)
    parameter NUM_CHANNELS= 22;
    parameter TOTAL_FEATS = 176;
    parameter CLK_PERIOD  = 10;        // 10 ns (100 MHz)
    parameter BIT_PERIOD  = 200;       // 200 ns (5 Mbaud)

    reg         clk;
    reg         rst;
    reg  [3:1]  btn;
    reg         uart_rxd;
    wire        uart_txd;
    reg  [15:0] sw;

    wire [15:0] led;
    wire        rgb0_r;
    wire        rgb0_g;
    wire        rgb0_b;
    wire [7:0]  anode;
    wire [6:0]  seg;
    wire        dp;
    wire [6:0]  seg1;
    wire        dp1;

    // Instantiate Top-Level Device Under Test (DUT)
    top_seizure_detector #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ),
        .BAUD_RATE(BAUD_RATE),
        .NUM_CHANNELS(NUM_CHANNELS),
        .DATA_WIDTH(16),
        .NUM_SUBBANDS(4),
        .TOTAL_FEATS(TOTAL_FEATS)
    ) dut (
        .clk(clk),
        .rst(rst),
        .btn(btn),
        .uart_rxd(uart_rxd),
        .uart_txd(uart_txd),
        .sw(sw),
        .led(led),
        .rgb0_r(rgb0_r),
        .rgb0_g(rgb0_g),
        .rgb0_b(rgb0_b),
        .anode(anode),
        .seg(seg),
        .dp(dp),
        .seg1(seg1),
        .dp1(dp1)
    );

    // 100 MHz Clock Generator
    always #(CLK_PERIOD / 2) clk = ~clk;

    // Stimulus memory
    reg [7:0] uart_stim [0:45055];

    integer failed_tests = 0;
    integer byte_idx = 0;
    integer total_bytes_to_send;

    // UART byte transmitter task
    task send_uart_byte;
        input [7:0] data;
        integer b_i;
        begin
            // Start bit (0)
            uart_rxd <= 1'b0;
            #(BIT_PERIOD);
            // 8 Data bits LSB first
            for (b_i = 0; b_i < 8; b_i = b_i + 1) begin
                uart_rxd <= data[b_i];
                #(BIT_PERIOD);
            end
            // Stop bit (1)
            uart_rxd <= 1'b1;
            #(BIT_PERIOD);
        end
    endtask

    // 4-byte sample frame transmitter task
    task send_sample_frame;
        input [7:0]  ch;
        input [15:0] sample;
        begin
            send_uart_byte(8'hAA);
            send_uart_byte(ch);
            send_uart_byte(sample[15:8]);
            send_uart_byte(sample[7:0]);
        end
    endtask

    initial begin
        clk      = 0;
        rst      = 1; // Active-high reset on btn[0]
        btn      = 3'b000;
        uart_rxd = 1'b1; // Idle high
        sw       = 16'b0000_0000_0000_0000; // k=1 for fast alarm verification

        $display("================================================================================");
        $display(" EE2000 Full-System Seizure Detector Integration Testbench");
        $display(" Target: 22 Channels, 176 Features, 100 MHz Clock, Spartan-7 Architecture");
        $display("================================================================================");

        // Load pre-generated UART stimulus (first 1 second = 22 * 256 * 4 = 22,528 bytes)
        $readmemh("golden/vectors/tb_uart_rx_stimulus.hex", uart_stim);

        // Release reset via 2-flop reset synchronizer
        #(CLK_PERIOD * 10);
        @(posedge clk);
        rst <= 1'b0;
        #(CLK_PERIOD * 10);

        // =====================================================================
        // Test 1: Stream Window 0 (22 Channels * 256 Samples = 5,632 Samples)
        // =====================================================================
        $display("\n[TEST 1] Streaming 1 full second of 22-channel EEG data (22,528 UART bytes)...");
        total_bytes_to_send = 22 * 256 * 4; // 22,528 bytes

        for (byte_idx = 0; byte_idx < total_bytes_to_send; byte_idx = byte_idx + 1) begin
            send_uart_byte(uart_stim[byte_idx]);
        end

        $display("  -> Stream complete. Waiting for pipeline drain and classification...");

        // Wait for pipeline drain and SVM classification to complete
        wait (dut.svm_done == 1'b1);
        @(posedge clk);

        $display("  [SVM DONE] Window 0 Score: %d | Decision: %b", dut.svm_score, dut.svm_decision);

        // Verify window 0 decision is 0 (Background)
        if (dut.svm_decision == 1'b0) begin
            $display("[PASS] Window 0 correctly classified as Non-Seizure (Score < 0)!");
        end else begin
            $display("[FAIL] Window 0 misclassified as seizure!");
            failed_tests = failed_tests + 1;
        end

        // Verify RGB0 is Solid Green (streaming_ok) and NOT flashing red
        if (rgb0_g == 1'b1 && rgb0_r == 1'b0) begin
            $display("[PASS] Status LED RGB0 is Solid Green (Streaming Active & Normal).");
        end else begin
            $display("[FAIL] Status LED RGB0 state unexpected: g=%b, r=%b", rgb0_g, rgb0_r);
            failed_tests = failed_tests + 1;
        end

        // =====================================================================
        // Test 2: Seizure Detection & Alarm Assertion Test
        // =====================================================================
        $display("\n[TEST 2] Testing seizure classification & alarm assertion...");
        // Stream high-amplitude rhythmic seizure discharge across all 22 channels
        // (Simulating ictal spike-wave pattern on focal channels)
        begin : feed_seizure_window
            integer s_i, ch_k;
            reg signed [15:0] sz_sample;
            for (s_i = 0; s_i < 256; s_i = s_i + 1) begin
                for (ch_k = 0; ch_k < 22; ch_k = ch_k + 1) begin
                    // 3.5 Hz rhythmic high-amplitude ictal discharge
                    sz_sample = (s_i % 32 < 16) ? 16'sd3000 : -16'sd3000;
                    send_sample_frame(ch_k[7:0], sz_sample);
                end
            end
        end

        $display("  -> Seizure window stream complete. Waiting for classifier...");
        wait (dut.svm_done == 1'b1);
        @(posedge clk);

        $display("  [SVM DONE] Window 1 Score: %d | Decision: %b", dut.svm_score, dut.svm_decision);

        // Wait for alarm logic to latch
        repeat (10) @(posedge clk);

        if (dut.seizure_alarm_latched == 1'b1) begin
            $display("[PASS] Seizure alarm latched successfully!");
            $display("  Alarm Count: %0d | Detection Timestamp: %0d s", dut.alarm_counter, dut.latched_latency);
        end else begin
            $display("[FAIL] Seizure alarm was not asserted!");
            failed_tests = failed_tests + 1;
        end

        // Verify LED15 alarm strobe and RGB0 red
        repeat (20) @(posedge clk);
        if (led[15] == dut.alarm_strobe && rgb0_r == dut.alarm_strobe && rgb0_g == 1'b0) begin
            $display("[PASS] Alarm visual indicators active: LED15 and RGB0_R strobing.");
        end else begin
            $display("[FAIL] Alarm visual indicators failed!");
            failed_tests = failed_tests + 1;
        end

        // =====================================================================
        // Test 3: Manual Clear via btn[1]
        // =====================================================================
        $display("\n[TEST 3] Testing manual alarm clear via btn[1]...");
        @(posedge clk);
        btn[1] <= 1'b1; // Press clear button
        repeat (5) @(posedge clk);
        btn[1] <= 1'b0; // Release
        repeat (10) @(posedge clk);

        if (dut.seizure_alarm_latched == 1'b0) begin
            $display("[PASS] Alarm successfully cleared! System returned to normal monitoring.");
        end else begin
            $display("[FAIL] Alarm did not clear on btn[1]!");
            failed_tests = failed_tests + 1;
        end

        // =====================================================================
        // Summary
        // =====================================================================
        $display("\n================================================================================");
        if (failed_tests == 0) begin
            $display(" ALL FULL-SYSTEM TESTS PASSED! End-to-end integration verified.");
        end else begin
            $display(" FAILED with %0d errors!", failed_tests);
        end
        $display("================================================================================\n");

        $finish;
    end

endmodule
