#!/bin/bash
# ==============================================================================
# Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
# Script: run_all.sh
# Purpose: Comprehensive regression suite running all self-checking testbenches
#          and generating an automated PASS/FAIL verification summary table.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo " EE2000 22-Channel EEG Seizure Detector – Automated Regression Suite"
echo " Target: Spartan-7 XC7S50 | Tool: Icarus Verilog / VVP"
echo "================================================================================"

PASSED_COUNT=0
FAILED_COUNT=0
RESULTS=()

run_test() {
    local name="$1"
    local sim_bin="$2"
    shift 2
    local src_files=("$@")

    printf "Running %-32s ... " "$name"
    if iverilog -g2001 -Wall -o "$sim_bin" "${src_files[@]}" > /dev/null 2>&1; then
        if vvp "$sim_bin" > "${sim_bin}.log" 2>&1; then
            if grep -Ei "ALL.*PASSED|TESTS PASSED" "${sim_bin}.log" > /dev/null 2>&1; then
                echo "[PASS]"
                RESULTS+=("$(printf "%-35s | PASS" "$name")")
                PASSED_COUNT=$((PASSED_COUNT + 1))
                return 0
            fi
        fi
    fi
    echo "[FAIL]"
    RESULTS+=("$(printf "%-35s | FAIL (see %s.log)" "$name" "$sim_bin")")
    FAILED_COUNT=$((FAILED_COUNT + 1))
    return 1
}

echo ""
echo "[1/7] Stage 1: UART RX Receiver & Framing Error Detector"
run_test "1. UART Receiver (tb_uart_rx)" "sim_uart_rx" rtl/uart_rx.v rtl/tb_uart_rx.v || true

echo "[2/7] Stage 2: 22-Channel Pipelined IIR Bandpass Filter"
run_test "2. IIR Biquad Filter (tb_iir_biquad)" "sim_iir_biquad" rtl/iir_biquad.v rtl/tb_iir_biquad.v || true

echo "[3/7] Stage 3: 5-Level Daubechies-4 DWT Cascade"
run_test "3. Multilevel DWT (tb_dwt_db4)" "sim_dwt_db4" rtl/dwt_level.v rtl/dwt_db4.v rtl/tb_dwt_db4.v || true

echo "[4/7] Stage 4: Ping-Pong Feature Accumulator"
run_test "4. Feature Accumulator (tb_feature_acc)" "sim_feature_accumulator" rtl/feature_accumulator.v rtl/tb_feature_accumulator.v || true

echo "[5/7] Stage 5: Linear SVM Classifier (176 Features)"
run_test "5. Linear SVM (tb_svm_classifier)" "sim_svm_classifier" rtl/svm_classifier.v rtl/tb_svm_classifier.v || true

echo "[6/7] Stage 6: Alarm Logic, Refractory & Telemetry"
run_test "6. Alarm Logic (tb_alarm_logic)" "sim_alarm_logic" rtl/alarm_logic.v rtl/uart_tx.v rtl/tb_alarm_logic.v || true

echo "[7/7] Stage 7: Full System Integration (tb_top)"
run_test "7. Full System Top (tb_top)" "sim_top" rtl/uart_rx.v rtl/iir_biquad.v rtl/dwt_level.v rtl/dwt_db4.v rtl/feature_accumulator.v rtl/svm_classifier.v rtl/alarm_logic.v rtl/uart_tx.v rtl/seven_seg_controller.v rtl/top_seizure_detector.v rtl/tb_top_seizure_detector.v || true

echo ""
echo "================================================================================"
echo " REGRESSION VERIFICATION SUMMARY"
echo "================================================================================"
for res in "${RESULTS[@]}"; do
    echo "  $res"
done
echo "--------------------------------------------------------------------------------"
TOTAL_COUNT=$((PASSED_COUNT + FAILED_COUNT))
echo " Total Passed: $PASSED_COUNT / $TOTAL_COUNT"
if [ "$FAILED_COUNT" -eq 0 ]; then
    echo " OVERALL STATUS: ALL REGRESSION TESTS PASSED (100% GREEN)"
else
    echo " OVERALL STATUS: $FAILED_COUNT TEST(S) FAILED"
fi
echo "================================================================================"

exit $FAILED_COUNT
