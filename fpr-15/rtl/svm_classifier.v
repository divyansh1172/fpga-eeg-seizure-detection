/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Module: svm_classifier
 * Purpose: 176-cycle serial multiply-accumulate linear SVM classifier for real-time
 *          EEG seizure detection.
 *          Evaluates the hyper-plane decision function:
 *            Score = b_fixed + sum_{j=0}^{175} (w_fixed[j] * feat[j])
 *            Decision = (Score > 0) ? 1'b1 : 1'b0 (1: Seizure, 0: Non-seizure)
 *          Features are signed 16-bit (Q15), weights are signed 16-bit (Q15),
 *          bias is signed 32-bit (Q30 equivalent scale), accumulator is 40-bit.
 *          Produces a clean 1-cycle done pulse upon classification completion.
 */

`timescale 1ns / 1ps

module svm_classifier #(
    parameter FEAT_DIM     = 176,
    parameter FEAT_WIDTH   = 16,
    parameter WEIGHT_WIDTH = 16,
    parameter BIAS_WIDTH   = 32,
    parameter ACCUM_WIDTH  = 40
)(
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire                              start,
    input  wire signed [FEAT_WIDTH-1:0]      feat_data,
    input  wire signed [WEIGHT_WIDTH-1:0]    weight_data,
    input  wire signed [BIAS_WIDTH-1:0]      bias_data,
    
    output reg                               done,
    output reg                               decision,
    output reg  signed [ACCUM_WIDTH-1:0]     score
);

    reg [8:0] count;
    reg signed [ACCUM_WIDTH-1:0] accum;
    reg running;

    // Sign extension of bias to 40-bit accumulator
    wire signed [ACCUM_WIDTH-1:0] bias_ext = { {(ACCUM_WIDTH-BIAS_WIDTH){bias_data[BIAS_WIDTH-1]}}, bias_data };
    // 16x16 -> 32-bit signed product
    wire signed [31:0] prod = feat_data * weight_data;
    // Sign extension of product to 40-bit accumulator
    wire signed [ACCUM_WIDTH-1:0] prod_ext = { {(ACCUM_WIDTH-32){prod[31]}}, prod };

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count    <= 9'd0;
            accum    <= {ACCUM_WIDTH{1'b0}};
            running  <= 1'b0;
            done     <= 1'b0;
            decision <= 1'b0;
            score    <= {ACCUM_WIDTH{1'b0}};
        end else if (start) begin
            count   <= 9'd1;
            accum   <= bias_ext + prod_ext;
            running <= 1'b1;
            done    <= 1'b0;
        end else if (running) begin
            if (count == FEAT_DIM - 1) begin
                running  <= 1'b0;
                done     <= 1'b1;
                score    <= accum + prod_ext;
                decision <= ((accum + prod_ext) > 0) ? 1'b1 : 1'b0;
                count    <= 9'd0;
            end else begin
                accum <= accum + prod_ext;
                count <= count + 1'b1;
            end
        end else begin
            done <= 1'b0;
        end
    end

endmodule
