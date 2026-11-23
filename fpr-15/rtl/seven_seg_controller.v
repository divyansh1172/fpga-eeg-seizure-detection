/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Team: 15
 * Author: Member 4 (Vivado Implementation & Board Demo Lead)
 * Purpose: Multiplexed dual 4-digit common-anode 7-segment display controller for
 *          the RealDigital Boolean Board (Spartan-7 XC7S50).
 *          Display 1 (Left 4 digits): Displays streaming playback time in seconds (0..9999).
 *          Display 0 (Right 4 digits): Displays seizure detection status ('IDLE' or 'SE' + latency).
 * AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Member 4)
 */

`timescale 1ns / 1ps

module seven_seg_controller #(
    parameter CLK_FREQ_HZ = 100000000,
    parameter REFRESH_HZ  = 1000       // 1 kHz multiplexing -> 125 Hz per digit
)(
    input  wire        clk,
    input  wire        rst_n,
    
    // Telemetry and status inputs
    input  wire [15:0] playback_time, // Elapsed streaming time in seconds
    input  wire [15:0] latency,       // Measured detection latency in seconds
    input  wire        alarm_active,  // 1: Seizure alarm asserted, 0: Normal streaming
    input  wire [7:0]  alarm_count,   // Total seizure alarms latched
    
    // RealDigital Boolean Board physical pin interface
    // Anodes: [3:0] for Display 0 (Right), [7:4] for Display 1 (Left)
    output reg  [7:0]  anode,         // Active-low digit enables (Pins D5, C4, C7, A8, H3, J4, F3, E4)
    
    // Display 0 (Right 4 digits - Status/Latency)
    output reg  [6:0]  seg,           // Active-low segment cathodes A..G (Pins D7, C5, A5, B7, A7, D6, B5)
    output reg         dp,            // Active-low decimal point (Pin A6)
    
    // Display 1 (Left 4 digits - Playback Time)
    output reg  [6:0]  seg1,          // Active-low segment cathodes A..G (Pins F4, J3, D2, C2, B1, H4, D1)
    output reg         dp1            // Active-low decimal point (Pin C1)
);

    localparam CLKS_PER_DIV = CLK_FREQ_HZ / REFRESH_HZ; // 100,000 clock cycles

    reg [16:0] clk_div;
    reg [2:0]  digit_idx;

    // Refresh divider and digit scanner (8 slots)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_div   <= 17'd0;
            digit_idx <= 3'd0;
        end else begin
            if (clk_div == CLKS_PER_DIV - 1) begin
                clk_div   <= 17'd0;
                digit_idx <= digit_idx + 1'b1;
            end else begin
                clk_div <= clk_div + 1'b1;
            end
        end
    end

    // Binary to 4-digit BCD for playback_time (Display 1, digits 7..4)
    wire [3:0] bcd_t_thousands = (playback_time / 1000) % 10;
    wire [3:0] bcd_t_hundreds  = (playback_time / 100) % 10;
    wire [3:0] bcd_t_tens      = (playback_time / 10) % 10;
    wire [3:0] bcd_t_units     = playback_time % 10;

    // Binary to 4-digit BCD for latency (Display 0, digits 3..0)
    wire [3:0] bcd_l_thousands = (latency / 1000) % 10;
    wire [3:0] bcd_l_hundreds  = (latency / 100) % 10;
    wire [3:0] bcd_l_tens      = (latency / 10) % 10;
    wire [3:0] bcd_l_units     = latency % 10;

    // Segment encoder function (active-low cathodes A..G for 0..9 and custom characters)
    // Segments: [6:0] = {G, F, E, D, C, B, A}
    function [6:0] encode_char;
        input [4:0] val;
        begin
            case (val)
                5'd0:  encode_char = 7'b1000000; // 0
                5'd1:  encode_char = 7'b1111001; // 1
                5'd2:  encode_char = 7'b0100100; // 2
                5'd3:  encode_char = 7'b0110000; // 3
                5'd4:  encode_char = 7'b0011001; // 4
                5'd5:  encode_char = 7'b0010010; // 5
                5'd6:  encode_char = 7'b0000010; // 6
                5'd7:  encode_char = 7'b1111000; // 7
                5'd8:  encode_char = 7'b0000000; // 8
                5'd9:  encode_char = 7'b0010000; // 9
                5'd10: encode_char = 7'b1111001; // 'I'
                5'd11: encode_char = 7'b0100001; // 'd'
                5'd12: encode_char = 7'b1000111; // 'L'
                5'd13: encode_char = 7'b0000110; // 'E'
                5'd14: encode_char = 7'b0010010; // 'S'
                5'd15: encode_char = 7'b0111111; // '-' (dash)
                default: encode_char = 7'b1111111; // Blank
            endcase
        end
    endfunction

    // 8-Digit Scanner
    always @(*) begin
        anode = 8'b11111111; // Default all digits off (active-low)
        dp    = 1'b1;        // Default DP off (active-low)
        seg   = 7'b1111111;  // Default segments off
        dp1   = 1'b1;        // Default DP1 off (active-low)
        seg1  = 7'b1111111;  // Default segments1 off

        case (digit_idx)
            // Digits 7..4: Display 1 (Playback Time, e.g. "2996")
            3'd7: begin
                anode = 8'b01111111; // Anode 7 (Pin E4)
                seg1  = encode_char({1'b0, bcd_t_thousands});
                seg   = 7'b1111111;
            end
            3'd6: begin
                anode = 8'b10111111; // Anode 6 (Pin F3)
                seg1  = encode_char({1'b0, bcd_t_hundreds});
                seg   = 7'b1111111;
            end
            3'd5: begin
                anode = 8'b11011111; // Anode 5 (Pin J4)
                seg1  = encode_char({1'b0, bcd_t_tens});
                seg   = 7'b1111111;
            end
            3'd4: begin
                anode = 8'b11101111; // Anode 4 (Pin H3)
                seg1  = encode_char({1'b0, bcd_t_units});
                seg   = 7'b1111111;
            end

            // Digits 3..0: Display 0 (Seizure "SE08" or Idle "IdLE")
            3'd3: begin
                anode = 8'b11110111; // Anode 3 (Pin A8)
                if (alarm_active)
                    seg = encode_char(5'd14); // 'S'
                else
                    seg = encode_char(5'd10); // 'I'
                seg1  = 7'b1111111;
            end
            3'd2: begin
                anode = 8'b11111011; // Anode 2 (Pin C7)
                if (alarm_active)
                    seg = encode_char(5'd13); // 'E'
                else
                    seg = encode_char(5'd11); // 'd'
                seg1  = 7'b1111111;
            end
            3'd1: begin
                anode = 8'b11111101; // Anode 1 (Pin C4)
                if (alarm_active)
                    seg = encode_char({1'b0, bcd_l_tens}); // Latency tens (e.g. 0)
                else
                    seg = encode_char(5'd12); // 'L'
                seg1  = 7'b1111111;
            end
            3'd0: begin
                anode = 8'b11111110; // Anode 0 (Pin D5)
                if (alarm_active)
                    seg = encode_char({1'b0, bcd_l_units}); // Latency units (e.g. 8)
                else
                    seg = encode_char(5'd13); // 'E'
                seg1  = 7'b1111111;
            end
        endcase
    end

endmodule
