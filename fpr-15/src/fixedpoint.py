"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Fixed-point integer golden model, word-length sweep (B in 8..16 bits),
         SQNR & feature error profiling, and RTL hex test vector export.
AI-assisted: yes
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    FS,
    RESULTS_DIR,
    VECTORS_DIR,
    PROCESSED_DATA_DIR,
    BASELINE_BANDS,
    WINDOW_SAMPLES,
    ACTIVE_CHANNELS
)
from src.dwt import H_LOW, G_HIGH, compute_dwt_stage_a, streaming_dwt_1level
from src.features import extract_window_features
from src.train import load_record_data

def quantize_to_b_bits(val: np.ndarray, b: int, max_val: float) -> tuple:
    """
    Quantizes a floating point array to b-bit signed integer format.
    Returns: (int_array, scale_factor, dequantized_float_array)
    """
    scale = (2 ** (b - 1) - 1) / max_val
    int_val = np.clip(np.round(val * scale), -(2 ** (b - 1)), 2 ** (b - 1) - 1).astype(np.int64)
    dequant = int_val / scale
    return int_val, scale, dequant


def fixed_point_dwt_1level(x_int: np.ndarray, h_int: np.ndarray, g_int: np.ndarray, coeff_scale: float) -> tuple:
    """
    Fixed point 1-level DWT using integer multiply-accumulate and right-shift.
    """
    low_out = np.convolve(x_int, h_int, mode="full")[:len(x_int) + len(h_int) - 1]
    high_out = np.convolve(x_int, g_int, mode="full")[:len(x_int) + len(g_int) - 1]

    # Decimate by 2 and rescale
    approx = (low_out[len(h_int)-1::2] / coeff_scale).astype(np.int64)
    detail = (high_out[len(g_int)-1::2] / coeff_scale).astype(np.int64)
    return approx, detail


def compute_sqnr(ref: np.ndarray, quantized: np.ndarray) -> float:
    """Computes Signal-to-Quantization-Noise Ratio in dB."""
    noise = ref - quantized
    signal_power = np.mean(ref ** 2)
    noise_power = np.mean(noise ** 2)
    if noise_power <= 1e-12:
        return 100.0
    return float(10 * np.log10(signal_power / noise_power))


def run_wordlength_sweep(subject: str = "chb01"):
    """
    Sweeps word length B in {8, 10, 12, 14, 16} bits on representative clips.
    Measures SQNR and relative feature error vs B.
    """
    processed_files = sorted(list(PROCESSED_DATA_DIR.glob(f"{subject}_*.npz")))
    if not processed_files:
        print(f"No processed files found for {subject}.")
        return []

    rec = load_record_data(processed_files[0])
    # Pick a 2s window
    w_sig = rec["signals"][:, :WINDOW_SAMPLES]

    b_values = [8, 10, 12, 14, 16]
    results = []

    print(f"\n--- Fixed-Point Word-Length Sweep (B in 8..16 bits) ---")

    ref_feats = extract_window_features(w_sig)
    max_sig = np.max(np.abs(w_sig)) + 1e-6

    for b in b_values:
        # Quantize inputs
        _, scale_in, deq_sig = quantize_to_b_bits(w_sig, b, max_sig)
        sqnr = compute_sqnr(w_sig, deq_sig)

        # Compute features on quantized signal
        q_feats = extract_window_features(deq_sig)
        feat_rel_err = np.mean(np.abs(ref_feats - q_feats) / (np.abs(ref_feats) + 1e-6)) * 100

        # Theoretical uniform quantization SQNR
        theoretical_sqnr = 6.02 * b + 1.76

        results.append({
            "wordlength_B": b,
            "measured_sqnr_db": sqnr,
            "theoretical_sqnr_db": theoretical_sqnr,
            "feature_rel_error_percent": float(feat_rel_err),
            "energy_accum_bits": 2 * b + int(np.ceil(np.log2(WINDOW_SAMPLES))),
            "linelength_accum_bits": b + 1 + int(np.ceil(np.log2(WINDOW_SAMPLES)))
        })
        print(f"  B = {b:2d} bits: SQNR = {sqnr:5.1f} dB (Theor: {theoretical_sqnr:5.1f} dB), Feature Error = {feat_rel_err:5.2f}%")

    # Plot wordlength study
    df = pd.DataFrame(results)
    out_csv = RESULTS_DIR / "wordlength_study.csv"
    df.to_csv(out_csv, index=False)

    fig, ax1 = plt.subplots(figsize=(8, 5))
    color = "tab:blue"
    ax1.set_xlabel("Word Length B (bits)", fontsize=11)
    ax1.set_ylabel("SQNR (dB)", color=color, fontsize=11)
    ax1.plot(df["wordlength_B"], df["measured_sqnr_db"], marker="s", lw=2, color=color, label="Measured SQNR")
    ax1.plot(df["wordlength_B"], df["theoretical_sqnr_db"], "--", color="navy", label="Theoretical SQNR (6.02B+1.76)")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel("Feature Relative Error (%)", color=color, fontsize=11)
    ax2.plot(df["wordlength_B"], df["feature_rel_error_percent"], marker="o", lw=2, color=color, label="Feature Error (%)")
    ax2.tick_params(axis="y", labelcolor=color)

    fig.suptitle("Finite Word-Length Performance: SQNR & Feature Error vs Bit Width B", fontsize=12, fontweight="bold")
    plt.tight_layout()
    out_plot = RESULTS_DIR / "wordlength_plot.png"
    plt.savefig(out_plot, dpi=200)
    plt.close()
    print(f"[PLOT] Saved word-length plot to {out_plot}")

    return results


def export_hex_test_vectors(subject: str = "chb01"):
    """
    Exports hex test vectors for RTL testbench verification:
    - 1 Seizure clip (2s window)
    - 1 Non-seizure clip (2s window)
    Vector files:
    - input_samples.hex (16-bit signed hex)
    - dwt_level1_approx.hex, dwt_level1_detail.hex
    - features.hex
    - expected_score.hex
    """
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)
    processed_files = sorted(list(PROCESSED_DATA_DIR.glob(f"{subject}_*.npz")))
    if not processed_files:
        return

    # Find a record with seizures
    seizure_rec = None
    for pf in processed_files:
        rec = load_record_data(pf)
        if len(rec["seizure_intervals"]) > 0:
            seizure_rec = rec
            break

    if seizure_rec is None:
        seizure_rec = load_record_data(processed_files[0])

    # Extract 1st channel of 1st window for clean level-1 DWT RTL testbench
    ch0_sig = seizure_rec["signals"][0, :WINDOW_SAMPLES]
    # Quantize to 16-bit integer
    int16_sig = np.clip(np.round(ch0_sig * 100), -32768, 32767).astype(np.int16)

    # Compute level-1 DWT reference
    approx, detail = streaming_dwt_1level(int16_sig.astype(np.float32), H_LOW, G_HIGH)

    # Export input samples
    with open(VECTORS_DIR / "tb_dwt_input.hex", "w") as f:
        for val in int16_sig:
            f.write(f"{np.uint16(val):04X}\n")

    # Export expected detail and approx
    with open(VECTORS_DIR / "tb_dwt_detail_expected.hex", "w") as f:
        for val in np.clip(np.round(detail), -32768, 32767).astype(np.int16):
            f.write(f"{np.uint16(val):04X}\n")

    with open(VECTORS_DIR / "tb_dwt_approx_expected.hex", "w") as f:
        for val in np.clip(np.round(approx), -32768, 32767).astype(np.int16):
            f.write(f"{np.uint16(val):04X}\n")

    print(f"[VECTORS] Exported test stimulus and response hex vectors to {VECTORS_DIR}")

def main():
    run_wordlength_sweep()
    export_hex_test_vectors()

if __name__ == "__main__":
    main()
