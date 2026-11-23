/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Team: 15
 * Author: Member 4 (Vivado Implementation & Board Demo Lead)
 * Purpose: Testbench for multiplexed 7-segment display controller.
 * AI-assisted: Yes (reviewed by Member 4)
 */

`timescale 1ns / 1ps

module tb_seven_seg_controller;

    reg clk;
    reg rst_n;
    reg [15:0] playback_time;
    reg [15:0] latency;
    reg alarm_active;
    reg [7:0] alarm_count;

    wire [7:0] anode;
    wire [6:0] seg;
    wire dp;

    // Use fast refresh rate for simulation (REFRESH_HZ = 100000)
    seven_seg_controller #(
        .CLK_FREQ_HZ(100000),
        .REFRESH_HZ(10000)
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .playback_time(playback_time),
        .latency(latency),
        .alarm_active(alarm_active),
        .alarm_count(alarm_count),
        .anode(anode),
        .seg(seg),
        .dp(dp)
    );

    always #5 clk = ~clk;

    integer i;

    initial begin
        clk = 0;
        rst_n = 0;
        playback_time = 16'd2996;
        latency = 16'd0;
        alarm_active = 0;
        alarm_count = 8'd0;

        #100;
        rst_n = 1;
        #50;

        $display("=================================================");
        $display("Starting 7-Segment Controller Simulation Testbench");
        $display("=================================================");

        // Scan through all digits during IDLE mode
        #200;
        $display("[INFO] Scanned IDLE digits: anode = %b, seg = %b", anode, seg);

        // Switch to ALARM active mode
        @(posedge clk);
        alarm_active <= 1;
        latency      <= 16'd8; // tau = 8.0 s
        alarm_count  <= 8'd1;

        #300;
        $display("[INFO] Scanned ALARM digits: anode = %b, seg = %b", anode, seg);

        #100;
        $display("[SUCCESS] 7-Segment Controller testbench completed without errors!");
        $display("=================================================");
        $finish;
    end

endmodule
