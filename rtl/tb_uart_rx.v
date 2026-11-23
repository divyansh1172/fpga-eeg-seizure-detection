/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: tb_uart_rx.v
 * Purpose: Self-checking testbench for UART receiver and packet framing FSM.
 * Tests:
 *   (a) Normal packet stream at 97.8% duty cycle.
 *   (b) Payload data bytes equal to 0xAA (MSB and LSB).
 *   (c) Dropped byte mid-packet (recovery and re-lock within <= 2 packets).
 *   (d) Framing error on corrupted stop bit.
 *   (e) False start bit / line glitch rejection.
 */

`timescale 1ns / 1ps

module tb_uart_rx;

    reg clk;
    reg rst_n;
    reg rxd;

    wire       byte_valid;
    wire [7:0] byte_data;
    wire       frame_err;

    // 100 MHz clock: period = 10 ns
    // 230,400 baud: 434 clocks per bit = 4340 ns per bit
    localparam CLK_PERIOD_NS = 10;
    localparam BIT_PERIOD_NS = 4340;

    // DUT: UART Receiver
    uart_rx #(
        .CLK_FREQ_HZ(100000000),
        .BAUD_RATE(230400)
    ) dut_rx (
        .clk(clk),
        .rst_n(rst_n),
        .rxd(rxd),
        .byte_valid(byte_valid),
        .byte_data(byte_data),
        .frame_err(frame_err)
    );

    // Packet Framing FSM (matching top_seizure_detector.v)
    reg [1:0] pkt_state;
    localparam PKT_SYNC = 2'd0;
    localparam PKT_CHAN = 2'd1;
    localparam PKT_MSB  = 2'd2;
    localparam PKT_LSB  = 2'd3;

    reg [4:0]  curr_ch;
    reg [7:0]  sample_msb;
    reg [15:0] sample_in;
    reg        sample_valid;
    reg [15:0] frame_count;
    reg [15:0] dropped_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pkt_state     <= PKT_SYNC;
            curr_ch       <= 5'd0;
            sample_msb    <= 8'd0;
            sample_in     <= 16'd0;
            sample_valid  <= 1'b0;
            frame_count   <= 16'd0;
            dropped_count <= 16'd0;
        end else begin
            sample_valid <= 1'b0;

            if (frame_err) begin
                pkt_state <= PKT_SYNC;
            end

            if (byte_valid) begin
                case (pkt_state)
                    PKT_SYNC: begin
                        if (byte_data == 8'hAA)
                            pkt_state <= PKT_CHAN;
                    end

                    PKT_CHAN: begin
                        if (byte_data < 22) begin
                            curr_ch   <= byte_data[4:0];
                            pkt_state <= PKT_MSB;
                        end else if (byte_data == 8'hAA) begin
                            pkt_state     <= PKT_CHAN;
                            dropped_count <= dropped_count + 1'b1;
                        end else begin
                            pkt_state     <= PKT_SYNC;
                            dropped_count <= dropped_count + 1'b1;
                        end
                    end

                    PKT_MSB: begin
                        sample_msb <= byte_data;
                        pkt_state  <= PKT_LSB;
                    end

                    PKT_LSB: begin
                        sample_in    <= {sample_msb, byte_data};
                        sample_valid <= 1'b1;
                        frame_count  <= frame_count + 1'b1;
                        pkt_state    <= PKT_SYNC;
                    end
                endcase
            end
        end
    end

    // 100 MHz clock generation
    always #(CLK_PERIOD_NS / 2) clk = ~clk;

    // UART Bit-Banging Tasks
    task send_byte(input [7:0] data, input stop_bit_val);
        integer i;
        begin
            // Start bit (0)
            rxd = 1'b0;
            #BIT_PERIOD_NS;

            // 8 Data bits (LSB first)
            for (i = 0; i < 8; i = i + 1) begin
                rxd = data[i];
                #BIT_PERIOD_NS;
            end

            // Stop bit
            rxd = stop_bit_val;
            #BIT_PERIOD_NS;
        end
    endtask

    task send_packet(input [4:0] ch, input [15:0] sample);
        begin
            send_byte(8'hAA, 1'b1);
            send_byte({3'b000, ch}, 1'b1);
            send_byte(sample[15:8], 1'b1);
            send_byte(sample[7:0], 1'b1);
        end
    endtask

    integer pass_count = 0;
    integer fail_count = 0;

    initial begin
        $display("================================================================");
        $display(" EE2000 TB_UART_RX: UART RX and Packet Framing Verification");
        $display("================================================================");

        clk   = 0;
        rst_n = 0;
        rxd   = 1'b1; // Idle line HIGH

        #100;
        rst_n = 1;
        #1000;

        // -------------------------------------------------------------
        // Test (a): Normal continuous stream (Channels 0 to 21) at 97.8% duty
        // -------------------------------------------------------------
        $display("[TEST A] Streaming normal 22-channel frame sequence...");
        begin : test_a
            integer ch_idx;
            for (ch_idx = 0; ch_idx < 22; ch_idx = ch_idx + 1) begin
                send_packet(ch_idx[4:0], 16'h1000 + ch_idx);
            end
        end
        #5000;
        if (frame_count == 22) begin
            $display("[PASS] Test (a): Received all 22 valid channel frames without drops (count=%0d).", frame_count);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test (a): Expected 22 frames, got %0d", frame_count);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // Test (b): Payload bytes equal to 0xAA (MSB and LSB)
        // -------------------------------------------------------------
        $display("[TEST B] Sending packet with 0xAA in payload bytes (sample = 0xAAAA)...");
        send_packet(5'd3, 16'hAAAA);
        #5000;
        if (sample_in == 16'hAAAA && curr_ch == 5'd3) begin
            $display("[PASS] Test (b): Payload 0xAA correctly parsed as sample data (ch=%0d, data=0x%04X).", curr_ch, sample_in);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test (b): Sample data corrupted: expected 0xAAAA, got 0x%04X", sample_in);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // Test (c): Dropped byte mid-packet (simulate lost byte)
        // -------------------------------------------------------------
        $display("[TEST C] Injecting dropped byte mid-packet and testing re-lock within <= 2 packets...");
        // Send partial truncated packet (only sync and channel, dropped MSB and LSB):
        send_byte(8'hAA, 1'b1);
        send_byte(8'd7, 1'b1);
        // Next packet 1 (may be sacrificed during re-lock):
        send_packet(5'd8, 16'h1234);
        // Next packet 2 (guaranteed re-lock):
        send_packet(5'd9, 16'h5678);
        #5000;
        if (sample_in == 16'h5678 && curr_ch == 5'd9) begin
            $display("[PASS] Test (c): FSM re-locked within 2 packets (ch=%0d, sample=0x%04X).", curr_ch, sample_in);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test (c): FSM failed to re-lock within 2 packets: ch=%0d, sample=0x%04X", curr_ch, sample_in);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // Test (d): Framing Error (corrupted stop bit = 0)
        // -------------------------------------------------------------
        $display("[TEST D] Injecting corrupted stop bit (stop_bit = 0)...");
        fork
            begin
                send_byte(8'h5A, 1'b0); // Stop bit driven low
                rxd = 1'b1;             // Return line to idle high
            end
            begin
                @(posedge frame_err);
                $display("[PASS] Test (d): Detected framing error pulse on corrupted stop bit!");
                pass_count = pass_count + 1;
            end
        join
        #10000; // Allow line to stabilize in IDLE

        // -------------------------------------------------------------
        // Test (e): Glitch / False start bit rejection
        // -------------------------------------------------------------
        $display("[TEST E] Injecting 100 ns glitch on idle line (< HALF_BIT = 2170 ns)...");
        rxd = 1'b0;
        #100; // Glitch lasting 100 ns (far shorter than half-bit 2170 ns)
        rxd = 1'b1;
        #10000;
        if (byte_valid == 1'b0 && dut_rx.state == 2'b00) begin
            $display("[PASS] Test (e): Glitch rejected; receiver remained in IDLE state.");
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test (e): False start bit triggered invalid byte reception! state=%b, byte_valid=%b", dut_rx.state, byte_valid);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // Final Summary
        // -------------------------------------------------------------
        $display("================================================================");
        if (fail_count == 0) begin
            $display(">>> ALL %0d TESTS PASSED! UART RX & PACKET FRAMING VERIFIED! <<<", pass_count);
        end else begin
            $display(">>> VERIFICATION FAILED: %0d FAILED, %0d PASSED <<<", fail_count, pass_count);
        end
        $display("================================================================");

        #1000;
        $finish;
    end

endmodule
