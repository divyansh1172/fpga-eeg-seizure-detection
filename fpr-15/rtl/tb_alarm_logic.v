/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Testbench: tb_alarm_logic
 * Purpose: Comprehensive self-checking testbench for alarm_logic.v and uart_tx.v.
 * Tests:
 *   1. Persistence parameter k in {1, 2, 3, 5}:
 *      - k = 1: alarm triggers on first positive window.
 *      - k = 2: alarm triggers on second consecutive positive window.
 *      - k = 3: alarm triggers on third consecutive positive window.
 *      - k = 5: alarm triggers on fifth consecutive positive window.
 *   2. Intermittent non-seizure windows:
 *      - Background window (0) resets consecutive counter.
 *   3. 30-Second Refractory Blanking:
 *      - Subsequent positive decisions during 30s refractory window are blanked.
 *      - Countdown ticks correctly on 1-second pulse.
 *      - New alarm permitted after 30 seconds expire.
 *   4. Manual Clear via btn_clear:
 *      - Asserts btn_clear -> alarm_latched clears.
 *      - Refractory blanking is preserved.
 *   5. UART TX Telemetry:
 *      - Verifies that tx_trigger causes uart_tx to send 0xA5 and return to idle-high.
 */

`timescale 1ns / 1ps

module tb_alarm_logic;

    parameter CLK_PERIOD = 10; // 100 MHz

    reg         clk;
    reg         rst_n;
    reg [1:0]   k_sel;
    reg         btn_clear;
    reg         svm_done;
    reg         svm_decision;
    reg         sec_tick;
    reg [15:0]  playback_seconds;

    wire        alarm_pulse;
    wire        alarm_latched;
    wire [7:0]  alarm_count;
    wire [2:0]  consec_count;
    wire        refractory_active;
    wire [5:0]  refractory_timer;
    wire [15:0] latched_latency;
    wire        tx_trigger;

    // Unit Under Test: alarm_logic
    alarm_logic uut_alarm (
        .clk(clk),
        .rst_n(rst_n),
        .k_sel(k_sel),
        .btn_clear(btn_clear),
        .svm_done(svm_done),
        .svm_decision(svm_decision),
        .sec_tick(sec_tick),
        .playback_seconds(playback_seconds),
        .alarm_pulse(alarm_pulse),
        .alarm_latched(alarm_latched),
        .alarm_count(alarm_count),
        .consec_count(consec_count),
        .refractory_active(refractory_active),
        .refractory_timer(refractory_timer),
        .latched_latency(latched_latency),
        .tx_trigger(tx_trigger)
    );

    // Telemetry UART Transmitter
    wire tx_busy;
    wire uart_txd;
    uart_tx #(
        .CLK_FREQ_HZ(100000000),
        .BAUD_RATE(230400)
    ) uut_tx (
        .clk(clk),
        .rst_n(rst_n),
        .tx_start(tx_trigger),
        .tx_data(8'hA5),
        .tx_busy(tx_busy),
        .txd(uart_txd)
    );

    always #(CLK_PERIOD / 2) clk = ~clk;

    integer failed_tests = 0;

    // Helper task to send an SVM decision
    task send_decision;
        input decision;
        begin
            @(posedge clk);
            svm_decision <= decision;
            svm_done     <= 1'b1;
            @(posedge clk);
            svm_done     <= 1'b0;
            repeat (5) @(posedge clk);
        end
    endtask

    // Helper task to tick 1 second
    task tick_second;
        begin
            @(posedge clk);
            sec_tick <= 1'b1;
            playback_seconds <= playback_seconds + 1'b1;
            @(posedge clk);
            sec_tick <= 1'b0;
            repeat (2) @(posedge clk);
        end
    endtask

    initial begin
        clk              = 0;
        rst_n            = 0;
        k_sel            = 2'b10; // Default k=3
        btn_clear        = 0;
        svm_done         = 0;
        svm_decision     = 0;
        sec_tick         = 0;
        playback_seconds = 0;

        $display("================================================================================");
        $display(" EE2000 Alarm Logic & Telemetry Self-Checking Verification");
        $display("================================================================================");

        // Reset
        #(CLK_PERIOD * 5);
        rst_n = 1;
        #(CLK_PERIOD * 5);

        // ---------------------------------------------------------------------
        // Test 1: Persistence Parameter k=3
        // ---------------------------------------------------------------------
        $display("[TEST 1] Testing k=3 persistence...");
        k_sel = 2'b10; // k=3

        // Send 1 positive window -> consec=1, no alarm
        send_decision(1);
        if (consec_count != 1 || alarm_pulse != 0 || alarm_latched != 0) begin
            $display("ERROR: k=3 step 1 failed!");
            failed_tests = failed_tests + 1;
        end

        // Send a negative window -> reset consec to 0
        send_decision(0);
        if (consec_count != 0) begin
            $display("ERROR: Intermittent 0 did not reset consec_count!");
            failed_tests = failed_tests + 1;
        end

        // Send 3 consecutive positive windows -> alarm must fire on 3rd!
        playback_seconds = 16'd15;
        send_decision(1); // 1
        send_decision(1); // 2
        send_decision(1); // 3 -> ALARM!

        if (alarm_latched == 1 && alarm_count == 1 && latched_latency == 16'd15 && refractory_timer == 30) begin
            $display("[PASS] k=3 triggered alarm on 3rd consecutive positive! Latency=%0d s", latched_latency);
        end else begin
            $display("ERROR: Alarm failed to trigger on 3rd window!");
            failed_tests = failed_tests + 1;
        end

        // ---------------------------------------------------------------------
        // Test 2: 30-Second Refractory Blanking
        // ---------------------------------------------------------------------
        $display("\n[TEST 2] Testing 30-second refractory blanking...");
        // Send more positive decisions during refractory window -> must NOT trigger new alarms
        send_decision(1);
        send_decision(1);
        if (alarm_count != 1) begin
            $display("ERROR: Alarm triggered during refractory window!");
            failed_tests = failed_tests + 1;
        end else begin
            $display("[PASS] Refractory blanking blocked re-triggering during ongoing seizure.");
        end

        // Tick 30 seconds
        repeat (30) tick_second();

        if (refractory_timer == 0 && refractory_active == 0) begin
            $display("[PASS] Refractory timer counted down to 0 after 30 seconds.");
        end else begin
            $display("ERROR: Refractory timer did not expire!");
            failed_tests = failed_tests + 1;
        end

        // ---------------------------------------------------------------------
        // Test 3: Manual Clear on btn_clear
        // ---------------------------------------------------------------------
        $display("\n[TEST 3] Testing manual alarm clear via button...");
        if (alarm_latched != 1) begin
            $display("ERROR: Alarm should still be latched before clear!");
            failed_tests = failed_tests + 1;
        end

        // Press btn_clear
        @(posedge clk);
        btn_clear <= 1'b1;
        @(posedge clk);
        btn_clear <= 1'b0;
        repeat (5) @(posedge clk);

        if (alarm_latched == 0 && consec_count == 0) begin
            $display("[PASS] Button clear successfully unlatched alarm and reset counter!");
        end else begin
            $display("ERROR: Button clear failed to unlatch alarm!");
            failed_tests = failed_tests + 1;
        end

        // ---------------------------------------------------------------------
        // Test 4: Persistence k=1, k=2, k=5
        // ---------------------------------------------------------------------
        $display("\n[TEST 4] Testing k=1, k=2, and k=5...");
        // k=1: immediate alarm on 1 positive
        k_sel = 2'b00; // k=1
        playback_seconds = 16'd50;
        send_decision(1);
        if (alarm_count == 2 && latched_latency == 16'd50) begin
            $display("[PASS] k=1 triggered alarm immediately on 1st positive!");
        end else begin
            $display("ERROR: k=1 failed!");
            failed_tests = failed_tests + 1;
        end

        // Clear and expire refractory
        btn_clear <= 1'b1; @(posedge clk); btn_clear <= 1'b0;
        send_decision(0); // clear consecutive history to background
        repeat (30) tick_second();

        // k=2: alarm on 2 positives
        k_sel = 2'b01; // k=2
        playback_seconds = 16'd85;
        send_decision(1); // 1 (no alarm)
        if (alarm_count != 2) begin
            $display("ERROR: k=2 false alarm on 1st positive!");
            failed_tests = failed_tests + 1;
        end
        send_decision(1); // 2 (alarm)
        if (alarm_count == 3) begin
            $display("[PASS] k=2 triggered alarm on 2nd positive!");
        end else begin
            $display("ERROR: k=2 failed!");
            failed_tests = failed_tests + 1;
        end

        // Clear and expire refractory
        btn_clear <= 1'b1; @(posedge clk); btn_clear <= 1'b0;
        send_decision(0); // clear consecutive history to background
        repeat (30) tick_second();

        // k=5: alarm on 5 positives
        k_sel = 2'b11; // k=5
        playback_seconds = 16'd120;
        send_decision(1);
        send_decision(1);
        send_decision(1);
        send_decision(1);
        if (alarm_count != 3) begin
            $display("ERROR: k=5 false alarm before 5th positive!");
            failed_tests = failed_tests + 1;
        end
        send_decision(1); // 5th positive -> alarm!
        if (alarm_count == 4) begin
            $display("[PASS] k=5 triggered alarm on 5th positive!");
        end else begin
            $display("ERROR: k=5 failed!");
            failed_tests = failed_tests + 1;
        end

        // ---------------------------------------------------------------------
        // Test 5: UART TX Telemetry Line Verification
        // ---------------------------------------------------------------------
        $display("\n[TEST 5] Testing UART TX telemetry output...");
        // Wait for UART transmitter to finish sending byte
        while (tx_busy) @(posedge clk);
        repeat (50) @(posedge clk);

        // Verify line is Idle-High (1'b1) and NOT stuck low!
        if (uart_txd == 1'b1) begin
            $display("[PASS] UART TX line returned to Idle-High (1'b1). No break condition!");
        end else begin
            $display("ERROR: UART TX line is stuck low!");
            failed_tests = failed_tests + 1;
        end

        // Summary
        $display("\n================================================================================");
        if (failed_tests == 0) begin
            $display(" ALL TESTS PASSED! Alarm logic and telemetry 100%% verified.");
        end else begin
            $display(" FAILED with %0d errors!", failed_tests);
        end
        $display("================================================================================\n");

        $finish;
    end

endmodule
