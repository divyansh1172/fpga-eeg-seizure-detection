/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: alarm_logic
 * Purpose: Unified alarm post-processing, persistence counting, 30-second refractory
 *          blanking, manual alarm clearing, and telemetry trigger.
 * Features:
 *   - Persistence parameter k in {1, 2, 3, 5} selectable via k_sel[1:0].
 *   - 30-second refractory blanking: initiates a 30-second refractory timer on alarm trigger
 *     to prevent repeated alarms during an ongoing ictal event.
 *   - Manual clear: btn_clear (debounced, edge-detected) clears alarm_latched and resets
 *     consecutive counter. Refractory blanking is preserved to avoid immediate re-alerting.
 *   - Latched detection timestamp: records the exact playback second of detection onset.
 *   - Telemetry strobe: pulses tx_trigger for 1-byte UART transmission to PC host.
 */

`timescale 1ns / 1ps

module alarm_logic (
    input  wire        clk,
    input  wire        rst_n,
    
    // User controls
    input  wire [1:0]  k_sel,              // 00: k=1, 01: k=2, 10: k=3, 11: k=5
    input  wire        btn_clear,          // Manual alarm clear button (edge-detected)
    
    // Pipeline events
    input  wire        svm_done,           // Pulsed on window classification completion
    input  wire        svm_decision,       // 1: Seizure positive, 0: Background
    input  wire        sec_tick,           // 1-second pulse (from hop_sync)
    input  wire [15:0] playback_seconds,   // Current playback time in seconds
    
    // Alarm outputs
    output reg         alarm_pulse,        // 1-cycle strobe on new alarm trigger
    output reg         alarm_latched,      // Asserted until cleared by btn_clear or reset
    output reg  [7:0]  alarm_count,        // Cumulative count of alarms fired
    output reg  [2:0]  consec_count,       // Current consecutive positive window count
    output wire        refractory_active,  // High while within 30-second refractory period
    output reg  [5:0]  refractory_timer,   // Refractory countdown timer (30 .. 0)
    output reg  [15:0] latched_latency,    // Playback second when alarm fired
    output reg         tx_trigger          // Strobe to trigger UART TX telemetry byte
);

    // Persistence mapping: 00 -> 1, 01 -> 2, 10 -> 3, 11 -> 5
    reg [2:0] k_thresh;
    always @(*) begin
        case (k_sel)
            2'b00: k_thresh = 3'd1;
            2'b01: k_thresh = 3'd2;
            2'b10: k_thresh = 3'd3;
            2'b11: k_thresh = 3'd5;
        endcase
    end

    assign refractory_active = (refractory_timer > 6'd0);

    // Button edge detector for clear
    reg btn_prev;
    wire btn_rise = btn_clear && !btn_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            btn_prev          <= 1'b0;
            alarm_pulse       <= 1'b0;
            alarm_latched     <= 1'b0;
            alarm_count       <= 8'd0;
            consec_count      <= 3'd0;
            refractory_timer  <= 6'd0;
            latched_latency   <= 16'd0;
            tx_trigger        <= 1'b0;
        end else begin
            btn_prev   <= btn_clear;
            alarm_pulse <= 1'b0;
            tx_trigger  <= 1'b0;

            // 1. Refractory 1-second timer tick
            if (sec_tick && (refractory_timer > 6'd0)) begin
                refractory_timer <= refractory_timer - 1'b1;
            end

            // 2. Manual alarm clear on button rise
            if (btn_rise) begin
                alarm_latched <= 1'b0;
                consec_count  <= 3'd0;
                // Note: refractory_timer is intentionally preserved to prevent immediate
                // re-alerting if the seizure discharge is still ongoing.
            end

            // 3. SVM decision processing
            if (svm_done) begin
                if (svm_decision) begin
                    if (consec_count < k_thresh) begin
                        consec_count <= consec_count + 1'b1;
                    end

                    // Check alarm trigger condition
                    if (((consec_count + 1'b1) >= k_thresh) && (refractory_timer == 6'd0)) begin
                        alarm_pulse      <= 1'b1;
                        alarm_latched    <= 1'b1;
                        alarm_count      <= alarm_count + 1'b1;
                        latched_latency  <= playback_seconds; // Record actual detection timestamp
                        refractory_timer <= 6'd30;            // Initiate 30-second refractory window
                        tx_trigger       <= 1'b1;             // Send telemetry status byte
                    end
                end else begin
                    consec_count <= 3'd0;
                end
            end
        end
    end

endmodule
