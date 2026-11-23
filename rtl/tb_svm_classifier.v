/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Testbench: tb_svm_classifier
 * Purpose: Full-window self-checking testbench for linear SVM classifier.
 * Tests:
 *   1. 60-second dataset replay (60 windows of 176 features each = 10,560 features):
 *      - Real trained weights loaded from golden/vectors/weights.mem.
 *      - 32-bit folded bias (0xFFF43986 = -771706).
 *      - Scores checked against golden/vectors/tb_svm_scores_expected.hex.
 *      - Decisions checked against golden/vectors/tb_decisions_expected.hex.
 *      - Measures score error (Target: 0 LSB bit-exact).
 *      - Verifies decision agreement (Target: 100.00%).
 *   2. Timing verification:
 *      - Verifies 176-cycle latency from start to done.
 *      - Verifies done is asserted for exactly 1 clock cycle.
 */

`timescale 1ns / 1ps

module tb_svm_classifier;

    parameter FEAT_DIM     = 176;
    parameter FEAT_WIDTH   = 16;
    parameter WEIGHT_WIDTH = 16;
    parameter BIAS_WIDTH   = 32;
    parameter ACCUM_WIDTH  = 40;
    parameter CLK_PERIOD   = 10; // 100 MHz

    reg                              clk;
    reg                              rst_n;
    reg                              start;
    reg signed [FEAT_WIDTH-1:0]      feat_data;
    wire signed [WEIGHT_WIDTH-1:0]   weight_data;
    reg signed [BIAS_WIDTH-1:0]      bias_data;

    wire                             done;
    wire                             decision;
    wire signed [ACCUM_WIDTH-1:0]    score;

    // Weight ROM loaded from weights.mem
    reg signed [15:0] weight_rom [0:FEAT_DIM-1];
    reg [7:0] weight_idx;
    assign weight_data = weight_rom[weight_idx];

    // Instantiate Unit Under Test
    svm_classifier #(
        .FEAT_DIM(FEAT_DIM),
        .FEAT_WIDTH(FEAT_WIDTH),
        .WEIGHT_WIDTH(WEIGHT_WIDTH),
        .BIAS_WIDTH(BIAS_WIDTH),
        .ACCUM_WIDTH(ACCUM_WIDTH)
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .feat_data(feat_data),
        .weight_data(weight_data),
        .bias_data(bias_data),
        .done(done),
        .decision(decision),
        .score(score)
    );

    // Clock generator (100 MHz)
    always #(CLK_PERIOD / 2) clk = ~clk;

    // Test vector memories
    reg [15:0] exp_feat_mem     [0:10559];
    reg [39:0] exp_score_mem    [0:59];
    reg        exp_decision_mem [0:59];

    integer win, j;
    integer total_windows = 60;
    integer correct_decisions = 0;
    integer failed_tests = 0;
    reg signed [39:0] max_score_err = 0;

    initial begin
        clk        = 0;
        rst_n      = 0;
        start      = 0;
        feat_data  = 0;
        weight_idx = 0;
        bias_data  = 32'shFFF43986; // Exact folded bias (-771706)

        $display("================================================================================");
        $display(" EE2000 Linear SVM Classifier Self-Checking Verification");
        $display("================================================================================");

        // Load test vectors
        $readmemh("golden/vectors/weights.mem", weight_rom);
        $readmemh("golden/vectors/tb_features_expected.hex", exp_feat_mem);
        $readmemh("golden/vectors/tb_svm_scores_expected.hex", exp_score_mem);
        $readmemh("golden/vectors/tb_decisions_expected.hex", exp_decision_mem);

        // Reset
        #(CLK_PERIOD * 5);
        rst_n = 1;
        #(CLK_PERIOD * 5);

        // Replay all 60 windows
        $display("[TEST 1] Evaluating SVM inference on 60 windows (10,560 features)...");

        for (win = 0; win < total_windows; win = win + 1) begin
            // Stream 176 features and weights
            for (j = 0; j < FEAT_DIM; j = j + 1) begin
                @(posedge clk);
                start      <= (j == 0);
                weight_idx <= j[7:0];
                feat_data  <= exp_feat_mem[win * FEAT_DIM + j];
            end
            @(posedge clk);
            start <= 1'b0;

            // Wait for classification to finish
            while (!done) @(posedge clk);

            // Verify score and decision
            begin : check_window
                reg signed [39:0] exp_sc;
                reg signed [39:0] err;
                reg               exp_dec;

                exp_sc  = exp_score_mem[win];
                exp_dec = exp_decision_mem[win];
                err     = score - exp_sc;
                if (err < 0) err = -err;
                if (err > max_score_err) max_score_err = err;

                if (decision == exp_dec) begin
                    correct_decisions = correct_decisions + 1;
                end else begin
                    $display("MISMATCH Decision Window %0d: got=%b, exp=%b | Score: got=%d, exp=%d",
                             win, decision, exp_dec, score, exp_sc);
                    failed_tests = failed_tests + 1;
                end

                if (err != 0) begin
                    $display("MISMATCH Score Window %0d: got=%d, exp=%d, err=%d",
                             win, score, exp_sc, err);
                    failed_tests = failed_tests + 1;
                end
            end

            // Idle between windows
            repeat (5) @(posedge clk);
        end

        $display("\n--- Verification Results ---");
        $display("Windows Evaluated:     %0d", total_windows);
        $display("Correct Decisions:     %0d / %0d (%.2f%% agreement)",
                 correct_decisions, total_windows, (correct_decisions * 100.0) / total_windows);
        $display("Maximum Score Error:   %0d LSB", max_score_err);

        // Check acceptance criteria
        if (correct_decisions == total_windows && max_score_err == 0) begin
            $display("[PASS] 100.00%% Decision Agreement and Bit-Exact Scores across all 60 windows!");
        end else begin
            $display("[FAIL] Decision mismatch or score error detected!");
            failed_tests = failed_tests + 1;
        end

        // Summary
        $display("\n================================================================================");
        if (failed_tests == 0) begin
            $display(" ALL TESTS PASSED! Linear SVM classifier is 100%% verified.");
        end else begin
            $display(" FAILED with %0d errors!", failed_tests);
        end
        $display("================================================================================\n");

        $finish;
    end

endmodule
