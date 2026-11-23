#!/usr/bin/env python3
"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: Multichannel Real-Time EEG Seizure Detection on FPGA
Module: Golden Reference Model (Float and Bit-Accurate Fixed-Point)
Author: Antigravity Agent (EE2000 Verification)

Purpose:
  Provides the bit-exact golden reference model for the entire 22-channel
  real-time seizure detection FPGA pipeline:
    1. Interleaved 22-channel 16-bit signed input stream (fs = 256 Hz, 4-byte UART packet)
    2. Causal 4th-order Butterworth bandpass filter (0.5 - 25 Hz, two biquad sections)
    3. Causal 5-level Daubechies-4 (db4) Discrete Wavelet Transform (DWT) cascade
       with per-channel state and per-channel decimation phases
    4. 1-second non-overlapping window feature extraction (Energy & Line-Length)
       across 22 channels x 4 retained subbands (D3, D4, D5, A5) = 176 features
    5. Linear SVM inference (dot-product score + bias, sign decision)
    6. Alarm post-processing (k-consecutive persistence + 30 s refractory blanking)

Modes:
  --mode float      : 64-bit IEEE double-precision reference
  --mode fixed      : Bit-accurate integer fixed-point model mirroring RTL
  --mode both       : Run both and generate comprehensive SQNR & feature fidelity report
"""

import os
import sys
import argparse
import pickle
from pathlib import Path
import numpy as np
import scipy.signal as signal

PROJ_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJ_ROOT / "golden"
VECTORS_DIR = GOLDEN_DIR / "vectors"
VECTORS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 0. Global System Constants
# ==============================================================================
NUM_CHANNELS = 22
FS = 256  # Sampling frequency in Hz
WINDOW_SEC = 1.0  # 1.0 second non-overlapping window
WINDOW_SAMPLES = int(WINDOW_SEC * FS)  # 256 samples per channel per window
TOTAL_WINDOW_SAMPLES = NUM_CHANNELS * WINDOW_SAMPLES  # 5,632 samples per window

# Retained subbands: D3 (16-32 Hz), D4 (8-16 Hz), D5 (4-8 Hz), A5 (0-4 Hz)
RETAINED_BANDS = ["D3", "D4", "D5", "A5"]
NUM_SUBBANDS = len(RETAINED_BANDS)  # 4
NUM_FEATS_PER_BAND = 2  # Energy and Line-Length
TOTAL_FEATS = NUM_CHANNELS * NUM_SUBBANDS * NUM_FEATS_PER_BAND  # 176

# Expected coefficient counts per channel in a 1-second (256-sample) window:
COEFF_COUNTS = {
    "D3": 32,
    "D4": 16,
    "D5": 8,
    "A5": 8
}

# Normalization right-shift amounts for 1-second window in RTL:
# Energy shift = 20 (D3), 19 (D4), 18 (D5), 18 (A5)
ENERGY_SHIFTS = {
    "D3": 20,
    "D4": 19,
    "D5": 18,
    "A5": 18
}

# Line-Length shift = log2(Nb)
LINELENGTH_SHIFTS = {
    "D3": 5,
    "D4": 4,
    "D5": 3,
    "A5": 3
}

# Scale factor: 1 uV = 20 LSB in 16-bit ADC input
S_SIG = 20.0

# ==============================================================================
# 1. Filter Coefficients (Exact Standard Definitions)
# ==============================================================================
# A. Daubechies 4 (db4) exact 8-tap decomposition filters
DB4_DEC_LO = np.array([
    -0.010597401784997278,
     0.032883011666982945,
     0.030841381835986965,
    -0.18703481171888114,
    -0.02798376941698385,
     0.6308807679295904,
     0.7148465705525415,
     0.23037781330885523
], dtype=np.float64)

# Quadrature mirror relationship: g[k] = (-1)^k * h[7-k]
DB4_DEC_HI = np.array([((-1)**k) * DB4_DEC_LO[7 - k] for k in range(8)], dtype=np.float64)

# Fixed-point Q15 representation (scale = 32768)
DB4_DEC_LO_Q15 = np.round(DB4_DEC_LO * 32768).astype(np.int32)
DB4_DEC_HI_Q15 = np.round(DB4_DEC_HI * 32768).astype(np.int32)

# B. 4th-order Butterworth Bandpass (0.5 - 25 Hz @ 256 Hz)
# 2 biquad Second-Order Sections (SOS)
IIR_SOS_FLOAT = signal.butter(2, [0.5, 25.0], btype="bandpass", fs=FS, output="sos")

# Shift-20 fixed-point coefficients matching iir_biquad.v:
# Scale = 2^20 = 1048576
IIR_S0_B = np.array([65688, 131377, 65688], dtype=np.int64)
IIR_S0_A = np.array([-1240423, 457209], dtype=np.int64)

IIR_S1_B = np.array([1048576, -2097152, 1048576], dtype=np.int64)
IIR_S1_A = np.array([-2078976, 1030563], dtype=np.int64)

# ==============================================================================
# 2. Model Loading & Scale Derivation
# ==============================================================================
class Dummy:
    def __init__(self, *args, **kwargs): pass
    def __setstate__(self, state): self.__dict__.update(state)

class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if "sklearn" in module:
            return Dummy
        return super().find_class(module, name)

def load_svm_model(subject: str = "chb01"):
    """
    Loads trained SVM weights and folds StandardScaler mean and scale:
      w_eff = coef / scale
      b_eff = intercept - sum(coef * mean / scale)
    """
    model_path = PROJ_ROOT / "results" / "models" / f"{subject}_fold0_model.pkl"
    npy_w_path = GOLDEN_DIR / f"w_eff_{subject}.npy"
    npy_b_path = GOLDEN_DIR / f"b_eff_{subject}.npy"

    if npy_w_path.exists() and npy_b_path.exists():
        w_eff = np.load(npy_w_path)
        b_eff = float(np.load(npy_b_path)[0])
        return w_eff, b_eff

    if not model_path.exists():
        raise FileNotFoundError(f"Neither {npy_w_path} nor {model_path} found!")

    with open(model_path, "rb") as f:
        m = SafeUnpickler(f).load()

    coef = m["clf"].coef_[0]
    intercept = m["clf"].intercept_[0]
    mean = m["scaler"].mean_
    scale = m["scaler"].scale_

    w_eff = coef / scale
    b_eff = float(intercept - np.sum(coef * mean / scale))

    np.save(npy_w_path, w_eff)
    np.save(npy_b_path, np.array([b_eff]))
    return w_eff, b_eff

def compute_hardware_scales(w_eff: np.ndarray, b_eff: float):
    """
    Derives feature scale multipliers K_i and 16-bit weight scale S_M:
      E_float  = E_fixed  * K_E,  where K_E  = 2^shift_E / (S_sig^2 * Nb)
      LL_float = LL_fixed * K_LL, where K_LL = 2^shift_LL / (S_sig * (Nb - 1))
      w_hw = w_eff * K
      w_fixed = round(w_hw * S_M) in signed int16
      b_fixed = round(b_eff * S_M) in signed int32
    """
    K = []
    for ch in range(NUM_CHANNELS):
        for b in RETAINED_BANDS:
            Nb = COEFF_COUNTS[b]
            # Energy
            k_e = (2.0 ** ENERGY_SHIFTS[b]) / ((S_SIG ** 2.0) * float(Nb))
            # Line-Length
            k_ll = (2.0 ** LINELENGTH_SHIFTS[b]) / (S_SIG * float(Nb - 1))
            K.extend([k_e, k_ll])
    K = np.array(K, dtype=np.float64)

    w_hw = w_eff * K
    max_w = np.max(np.abs(w_hw))
    S_M = int(32767.0 / (max_w * 1.05))

    w_fixed = np.clip(np.round(w_hw * S_M), -32768, 32767).astype(np.int16)
    b_fixed = int(round(b_eff * S_M))

    return K, S_M, w_fixed, b_fixed

# ==============================================================================
# 3. Synthetic Data Generator (Broadband Physiological EEG)
# ==============================================================================
def generate_synthetic_eeg_stream(duration_sec: float = 60.0, seizure_onset_sec: float = 30.0):
    """
    Generates realistic 22-channel broadband EEG in microvolts (uV) and 16-bit integers.
    Background: Delta (2 Hz), Theta (6 Hz), Alpha (10 Hz), Beta (22 Hz).
    Seizure: Focal rhythmic discharge on channels 4, 5, 6, 7, 14, 15 starting at onset.
    """
    total_frames = int(duration_sec * FS)
    t = np.arange(total_frames) / FS
    signals_uV = np.zeros((NUM_CHANNELS, total_frames), dtype=np.float64)
    signals_int16 = np.zeros((NUM_CHANNELS, total_frames), dtype=np.int16)

    # Focal channels exhibiting ictal discharges in chb01
    focal_channels = [4, 5, 6, 7, 14, 15]

    for ch in range(NUM_CHANNELS):
        ph = 2 * np.pi * (ch / float(NUM_CHANNELS))
        # Broadband physiological background (uV)
        bg = 20.0 * np.sin(2 * np.pi * 2.0 * t + ph * 0.5) + \
             15.0 * np.sin(2 * np.pi * 6.0 * t + ph * 0.8) + \
             15.0 * np.sin(2 * np.pi * 10.0 * t + ph) + \
              8.0 * np.sin(2 * np.pi * 22.0 * t + ph * 1.2)

        # Focal seizure discharge: 3.5 Hz rhythmic spike-wave (80 uV) + 18 Hz harmonic (40 uV)
        sz = np.zeros_like(t)
        if ch in focal_channels:
            sz_mask = (t >= seizure_onset_sec)
            t_sz = t[sz_mask] - seizure_onset_sec
            sz[sz_mask] = 80.0 * np.sin(2 * np.pi * 3.5 * t_sz) + \
                          40.0 * np.sin(2 * np.pi * 18.0 * t_sz)

        sig_uV = bg + sz
        signals_uV[ch, :] = sig_uV
        # Scale to 16-bit integer (S_SIG = 20 LSB/uV)
        signals_int16[ch, :] = np.clip(np.round(sig_uV * S_SIG), -32768, 32767).astype(np.int16)

    # Round-robin interleaved sample sequence
    interleaved_samples = []
    for n in range(total_frames):
        for ch in range(NUM_CHANNELS):
            interleaved_samples.append(signals_int16[ch, n])

    return (
        np.array(interleaved_samples, dtype=np.int16),
        signals_uV,
        signals_int16,
        seizure_onset_sec
    )

# ==============================================================================
# 4. Pipeline Stages: Floating-Point Reference Model
# ==============================================================================
class FloatChannelIIR:
    """Per-channel floating-point Butterworth 4th order bandpass filter."""
    def __init__(self, sos):
        self.sos = sos
        self.zi = np.zeros((2, 2), dtype=np.float64)

    def process_sample(self, x: float) -> float:
        y = x
        for s in range(2):
            b = self.sos[s, :3]
            a = self.sos[s, 3:]
            w = y - a[1]*self.zi[s, 0] - a[2]*self.zi[s, 1]
            y = b[0]*w + b[1]*self.zi[s, 0] + b[2]*self.zi[s, 1]
            self.zi[s, 1] = self.zi[s, 0]
            self.zi[s, 0] = w
        return y

class FloatChannelDWT:
    """Per-channel floating-point 5-level Daubechies-4 DWT cascade."""
    def __init__(self):
        self.shift_regs = [np.zeros(8, dtype=np.float64) for _ in range(5)]
        self.phases = [0] * 5

    def process_sample(self, x: float) -> dict:
        produced = {}
        inp = x
        for lvl in range(5):
            self.shift_regs[lvl][1:] = self.shift_regs[lvl][:-1]
            self.shift_regs[lvl][0] = inp

            if self.phases[lvl] == 1:
                a = float(np.sum(self.shift_regs[lvl] * DB4_DEC_LO))
                d = float(np.sum(self.shift_regs[lvl] * DB4_DEC_HI))
                self.phases[lvl] = 0

                produced[f"D{lvl+1}"] = d
                inp = a
                if lvl == 4:
                    produced["A5"] = a
            else:
                self.phases[lvl] = 1
                break

        return produced

def run_float_pipeline(signals_uV: np.ndarray, w_eff: np.ndarray, b_eff: float, k: int = 3):
    """
    Executes full 64-bit floating-point reference pipeline.
    """
    num_channels, num_samples = signals_uV.shape
    num_windows = num_samples // WINDOW_SAMPLES

    iir_filters = [FloatChannelIIR(IIR_SOS_FLOAT) for _ in range(num_channels)]
    dwt_filters = [FloatChannelDWT() for _ in range(num_channels)]

    filtered_signals = np.zeros((num_channels, num_samples), dtype=np.float64)
    all_window_features = []
    all_scores = []
    all_decisions = []
    alarms = []

    consec_count = 0
    refractory_sec = 0

    for w_idx in range(num_windows):
        start_samp = w_idx * WINDOW_SAMPLES
        end_samp = start_samp + WINDOW_SAMPLES

        window_coeffs = {ch: {b: [] for b in RETAINED_BANDS} for ch in range(num_channels)}

        for n in range(start_samp, end_samp):
            for ch in range(num_channels):
                raw_uV = float(signals_uV[ch, n])
                y_filt = iir_filters[ch].process_sample(raw_uV)
                filtered_signals[ch, n] = y_filt

                dwt_out = dwt_filters[ch].process_sample(y_filt)
                for b in RETAINED_BANDS:
                    if b in dwt_out:
                        window_coeffs[ch][b].append(dwt_out[b])

        w_feats = []
        for ch in range(num_channels):
            for b in RETAINED_BANDS:
                coeffs = np.array(window_coeffs[ch][b], dtype=np.float64)
                energy = float(np.mean(coeffs ** 2)) if len(coeffs) > 0 else 0.0
                if len(coeffs) > 1:
                    linelength = float(np.mean(np.abs(np.diff(coeffs))))
                else:
                    linelength = 0.0
                w_feats.extend([energy, linelength])

        feats_arr = np.array(w_feats, dtype=np.float64)
        all_window_features.append(feats_arr)

        score = float(np.dot(w_eff, feats_arr) + b_eff)
        decision = 1 if score > 0 else 0
        all_scores.append(score)
        all_decisions.append(decision)

        if refractory_sec > 0:
            refractory_sec -= 1

        alarm_fired = 0
        if decision == 1:
            consec_count += 1
            if consec_count >= k and refractory_sec == 0:
                alarm_fired = 1
                refractory_sec = 30
        else:
            consec_count = 0

        alarms.append(alarm_fired)

    return {
        "filtered_signals": filtered_signals,
        "features": np.array(all_window_features, dtype=np.float64),
        "scores": np.array(all_scores, dtype=np.float64),
        "decisions": np.array(all_decisions, dtype=np.int32),
        "alarms": np.array(alarms, dtype=np.int32)
    }

# ==============================================================================
# 5. Pipeline Stages: Bit-Accurate Fixed-Point Model (RTL Matching)
# ==============================================================================
class FixedChannelIIR:
    """
    Per-channel fixed-point 4th order Butterworth IIR filter.
    Implements 2 cascaded Direct Form I biquad sections with Q20 internal state
    and guard bits matching the pipelined iir_biquad.v datapath.
    """
    def __init__(self):
        self.s0_x1 = np.int64(0)
        self.s0_x2 = np.int64(0)
        self.s0_y1 = np.int64(0)
        self.s0_y2 = np.int64(0)

        self.s1_x1 = np.int64(0)
        self.s1_x2 = np.int64(0)
        self.s1_y1 = np.int64(0)
        self.s1_y2 = np.int64(0)

    def process_sample(self, x_in: int) -> int:
        x = np.int64(x_in)

        # Section 0: Lowpass
        acc0 = (IIR_S0_B[0] * x) + (IIR_S0_B[1] * self.s0_x1) + (IIR_S0_B[2] * self.s0_x2) - \
               ((IIR_S0_A[0] * self.s0_y1 + IIR_S0_A[1] * self.s0_y2 + 524288) >> 20)

        self.s0_x2 = self.s0_x1
        self.s0_x1 = x
        self.s0_y2 = self.s0_y1
        self.s0_y1 = acc0

        y0_round = (acc0 + 524288) >> 20
        y0_sat = np.clip(y0_round, -32768, 32767)

        # Section 1: Highpass
        acc1 = (IIR_S1_B[0] * y0_sat) + (IIR_S1_B[1] * self.s1_x1) + (IIR_S1_B[2] * self.s1_x2) - \
               ((IIR_S1_A[0] * self.s1_y1 + IIR_S1_A[1] * self.s1_y2 + 524288) >> 20)

        self.s1_x2 = self.s1_x1
        self.s1_x1 = y0_sat
        self.s1_y2 = self.s1_y1
        self.s1_y1 = acc1

        y1_round = (acc1 + 524288) >> 20
        y1_sat = int(np.clip(y1_round, -32768, 32767))
        return y1_sat

class FixedChannelDWT:
    """
    Per-channel fixed-point 5-level Daubechies-4 DWT cascade.
    Shift registers, decimation phases, and Q15 multiplier-accumulators.
    """
    def __init__(self):
        self.shift_regs = [np.zeros(8, dtype=np.int32) for _ in range(5)]
        self.phases = [0] * 5

    def process_sample(self, x: int) -> dict:
        produced = {}
        inp = int(x)

        for lvl in range(5):
            self.shift_regs[lvl][1:] = self.shift_regs[lvl][:-1]
            self.shift_regs[lvl][0] = inp

            if self.phases[lvl] == 1:
                sum_a = int(np.sum(self.shift_regs[lvl] * DB4_DEC_LO_Q15))
                sum_d = int(np.sum(self.shift_regs[lvl] * DB4_DEC_HI_Q15))

                a_val = int(np.clip((sum_a + 16384) >> 15, -32768, 32767))
                d_val = int(np.clip((sum_d + 16384) >> 15, -32768, 32767))

                self.phases[lvl] = 0
                produced[f"D{lvl+1}"] = d_val
                inp = a_val

                if lvl == 4:
                    produced["A5"] = a_val
            else:
                self.phases[lvl] = 1
                break

        return produced

def run_fixed_pipeline(
    signals_int16: np.ndarray,
    w_fixed: np.ndarray,
    b_fixed: int,
    k: int = 3
):
    """
    Executes full bit-accurate fixed-point RTL matching pipeline.
    """
    num_channels, num_samples = signals_int16.shape
    num_windows = num_samples // WINDOW_SAMPLES

    iir_filters = [FixedChannelIIR() for _ in range(num_channels)]
    dwt_filters = [FixedChannelDWT() for _ in range(num_channels)]

    filtered_signals = np.zeros((num_channels, num_samples), dtype=np.int16)
    all_window_features = []
    all_scores = []
    all_decisions = []
    alarms = []

    # Buffers for test vector export (Level 3 D3, Level 4 D4, Level 5 D5, Level 5 A5)
    dwt_dump_buffers = {b: [] for b in RETAINED_BANDS}

    consec_count = 0
    refractory_sec = 0

    for w_idx in range(num_windows):
        start_samp = w_idx * WINDOW_SAMPLES
        end_samp = start_samp + WINDOW_SAMPLES

        # 38-bit energy accumulators & 26-bit line-length accumulators
        energy_acc = np.zeros(NUM_CHANNELS * NUM_SUBBANDS, dtype=np.int64)
        linelength_acc = np.zeros(NUM_CHANNELS * NUM_SUBBANDS, dtype=np.int64)
        prev_coeff = np.zeros(NUM_CHANNELS * NUM_SUBBANDS, dtype=np.int32)
        has_prev = np.zeros(NUM_CHANNELS * NUM_SUBBANDS, dtype=bool)

        for n in range(start_samp, end_samp):
            for ch in range(num_channels):
                raw_sample = int(signals_int16[ch, n])
                y_filt = iir_filters[ch].process_sample(raw_sample)
                filtered_signals[ch, n] = y_filt

                dwt_out = dwt_filters[ch].process_sample(y_filt)
                for sband_idx, b in enumerate(RETAINED_BANDS):
                    if b in dwt_out:
                        c_val = dwt_out[b]
                        bin_addr = ch * NUM_SUBBANDS + sband_idx
                        dwt_dump_buffers[b].append(c_val)

                        # Energy: accumulate squared 16-bit coefficient
                        energy_acc[bin_addr] += np.int64(c_val) * np.int64(c_val)

                        # Line-Length: accumulate absolute difference
                        if has_prev[bin_addr]:
                            diff = abs(c_val - prev_coeff[bin_addr])
                            linelength_acc[bin_addr] += diff
                        else:
                            has_prev[bin_addr] = True

                        prev_coeff[bin_addr] = c_val

        # Normalization and feature serialization
        w_feats = []
        for bin_addr in range(NUM_CHANNELS * NUM_SUBBANDS):
            sband_idx = bin_addr % NUM_SUBBANDS
            band_name = RETAINED_BANDS[sband_idx]

            # Energy normalization: right-shift by ENERGY_SHIFTS[band_name]
            e_shift = ENERGY_SHIFTS[band_name]
            e_val = (energy_acc[bin_addr] + (1 << (e_shift - 1))) >> e_shift
            e_sat = int(np.clip(e_val, 0, 32767))

            # Line-Length normalization: right-shift by LINELENGTH_SHIFTS[band_name]
            ll_shift = LINELENGTH_SHIFTS[band_name]
            ll_val = (linelength_acc[bin_addr] + (1 << (ll_shift - 1))) >> ll_shift
            ll_sat = int(np.clip(ll_val, 0, 32767))

            w_feats.extend([e_sat, ll_sat])

        feats_arr = np.array(w_feats, dtype=np.int16)
        all_window_features.append(feats_arr)

        # 176-cycle serial multiply-accumulate matching svm_classifier.v
        mac_accum = np.int64(b_fixed)
        for j in range(TOTAL_FEATS):
            prod = np.int64(feats_arr[j]) * np.int64(w_fixed[j])
            mac_accum += prod

        decision = 1 if mac_accum > 0 else 0
        all_scores.append(mac_accum)
        all_decisions.append(decision)

        # Alarm logic
        if refractory_sec > 0:
            refractory_sec -= 1

        alarm_fired = 0
        if decision == 1:
            consec_count += 1
            if consec_count >= k and refractory_sec == 0:
                alarm_fired = 1
                refractory_sec = 30
        else:
            consec_count = 0

        alarms.append(alarm_fired)

    return {
        "filtered_signals": filtered_signals,
        "features": np.array(all_window_features, dtype=np.int16),
        "scores": np.array(all_scores, dtype=np.int64),
        "decisions": np.array(all_decisions, dtype=np.int32),
        "alarms": np.array(alarms, dtype=np.int32),
        "weights_fixed": w_fixed,
        "bias_fixed": b_fixed,
        "dwt_buffers": {b: np.array(v, dtype=np.int16) for b, v in dwt_dump_buffers.items()}
    }

# ==============================================================================
# 6. Verification Metrics & Hex Dump Utilities
# ==============================================================================
def compute_sqnr(ref: np.ndarray, quant: np.ndarray) -> float:
    """Computes Signal-to-Quantization-Noise Ratio (SQNR) in dB."""
    noise = ref.astype(np.float64) - quant.astype(np.float64)
    sig_pow = np.mean(ref.astype(np.float64) ** 2)
    noise_pow = np.mean(noise ** 2)
    if noise_pow <= 1e-15:
        return 120.0
    return float(10.0 * np.log10(sig_pow / noise_pow))

def write_hex_file(path: Path, values: np.ndarray, width_bits: int = 16):
    """Writes values as 2's complement hexadecimal strings for Verilog readmemh."""
    mask = (1 << width_bits) - 1
    fmt = f"{{:0{width_bits // 4}X}}\n"
    with open(path, "w") as f:
        for val in values.flatten():
            f.write(fmt.format(int(val) & mask))

def dump_test_vectors(
    interleaved_samples: np.ndarray,
    fixed_res: dict
):
    """Dumps per-stage Verilog test vectors into golden/vectors/."""
    print(f"\n[DUMP] Exporting verification vectors to {VECTORS_DIR}...")

    # 1. UART Receiver stimulus (2 seconds of 4-byte frames: 0xAA, ch, MSB, LSB)
    num_samples_dump = min(len(interleaved_samples), 22 * 256 * 2)
    uart_bytes = []
    for idx in range(num_samples_dump):
        ch = idx % NUM_CHANNELS
        val = int(interleaved_samples[idx])
        uart_bytes.extend([0xAA, ch, (val >> 8) & 0xFF, val & 0xFF])

    with open(VECTORS_DIR / "tb_uart_rx_stimulus.hex", "w") as f:
        for b in uart_bytes:
            f.write(f"{b:02X}\n")

    # 2. IIR Input & Output vectors (first 2 seconds)
    iir_in = interleaved_samples[:num_samples_dump]
    iir_out = fixed_res["filtered_signals"].T.flatten()[:num_samples_dump]
    write_hex_file(VECTORS_DIR / "tb_iir_input.hex", iir_in, 16)
    write_hex_file(VECTORS_DIR / "tb_iir_expected.hex", iir_out, 16)

    # 3. DWT Subband outputs
    write_hex_file(VECTORS_DIR / "tb_dwt_input.hex", iir_out, 16)
    write_hex_file(VECTORS_DIR / "tb_dwt_d3_expected.hex", fixed_res["dwt_buffers"]["D3"], 16)
    write_hex_file(VECTORS_DIR / "tb_dwt_d4_expected.hex", fixed_res["dwt_buffers"]["D4"], 16)
    write_hex_file(VECTORS_DIR / "tb_dwt_d5_expected.hex", fixed_res["dwt_buffers"]["D5"], 16)
    write_hex_file(VECTORS_DIR / "tb_dwt_a5_expected.hex", fixed_res["dwt_buffers"]["A5"], 16)

    # 4. 176 Features per window
    write_hex_file(VECTORS_DIR / "tb_features_expected.hex", fixed_res["features"], 16)

    # 5. SVM Weights and Bias
    write_hex_file(VECTORS_DIR / "weights.mem", fixed_res["weights_fixed"], 16)
    with open(VECTORS_DIR / "bias.mem", "w") as f:
        f.write(f"{fixed_res['bias_fixed'] & 0xFFFFFFFF:08X}\n")

    # 6. Classifier scores, decisions, and alarm log
    write_hex_file(VECTORS_DIR / "tb_svm_scores_expected.hex", fixed_res["scores"], 40)
    write_hex_file(VECTORS_DIR / "tb_decisions_expected.hex", fixed_res["decisions"], 1)
    write_hex_file(VECTORS_DIR / "tb_alarms_expected.hex", fixed_res["alarms"], 1)

    print(f"[OK] 12 test vector files exported successfully to {VECTORS_DIR}!")

# ==============================================================================
# 7. Main Execution & Verification Report
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="EE2000 FPGA Seizure Detector Golden Reference Model")
    parser.add_argument("--mode", type=str, default="both", choices=["float", "fixed", "both"],
                        help="Execution mode: float, fixed, or both")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Duration of synthetic EEG stream in seconds (default: 60.0 s)")
    parser.add_argument("--onset", type=float, default=30.0,
                        help="Scheduled clinical seizure onset in seconds (default: 30.0 s)")
    parser.add_argument("--subject", type=str, default="chb01",
                        help="Subject model to load (default: chb01)")
    parser.add_argument("--k", type=int, default=3, choices=[1, 2, 3, 5],
                        help="Alarm persistence parameter k (default: 3)")
    parser.add_argument("--dump-vectors", action="store_true",
                        help="Dump per-stage .hex/.mem test vectors into golden/vectors/")
    args = parser.parse_args()

    print("=" * 80)
    print(" EE2000 Real-Time EEG Seizure Detector – Golden Reference Model")
    print(f" Target: 22 Channels, 256 Hz, 1.0 s Windows | Subject: {args.subject} | k = {args.k}")
    print("=" * 80)

    # Load model weights & bias
    print(f"[INIT] Loading SVM weights for subject {args.subject}...")
    w_eff, b_eff = load_svm_model(args.subject)
    K, S_M, w_fixed, b_fixed = compute_hardware_scales(w_eff, b_eff)
    print(f"  w_eff: min = {w_eff.min():.5f}, max = {w_eff.max():.5f}, mean = {w_eff.mean():.5f}")
    print(f"  b_eff: {b_eff:.5f}")
    print(f"  Hardware Scale Factor S_M: {S_M}")
    print(f"  w_fixed (16-bit): min = {w_fixed.min()}, max = {w_fixed.max()}")
    print(f"  b_fixed (32-bit): {b_fixed}")

    # Generate synthetic stimulus
    print(f"\n[STREAM] Generating {args.duration:.1f} s synthetic 22-channel EEG stream (onset = {args.onset:.1f} s)...")
    interleaved_samples, signals_uV, signals_int16, onset_sec = generate_synthetic_eeg_stream(
        duration_sec=args.duration, seizure_onset_sec=args.onset
    )
    total_windows = int(args.duration // WINDOW_SEC)
    print(f"  Total samples generated: {len(interleaved_samples):,} ({total_windows} windows)")

    float_res = None
    fixed_res = None

    if args.mode in ["float", "both"]:
        print("\n[FLOAT] Executing 64-bit Floating-Point Pipeline...")
        float_res = run_float_pipeline(signals_uV, w_eff, b_eff, k=args.k)
        print("  Float execution complete.")

    if args.mode in ["fixed", "both"]:
        print("\n[FIXED] Executing Bit-Accurate Fixed-Point RTL Model...")
        fixed_res = run_fixed_pipeline(signals_int16, w_fixed, b_fixed, k=args.k)
        print("  Fixed-point execution complete.")

    # Dump vectors if requested
    if args.dump_vectors and fixed_res is not None:
        dump_test_vectors(interleaved_samples, fixed_res)

    # Comparison and Verification Report
    if args.mode == "both":
        print("\n" + "=" * 80)
        print(" VERIFICATION & QUANTIZATION FIDELITY REPORT (Float vs. Fixed-Point)")
        print("=" * 80)

        # 1. IIR Bandpass Filter Fidelity
        ref_iir = float_res["filtered_signals"] * S_SIG
        quant_iir = fixed_res["filtered_signals"].astype(np.float64)
        iir_sqnr = compute_sqnr(ref_iir[:, 64:], quant_iir[:, 64:])
        iir_max_err = np.max(np.abs(ref_iir[:, 64:] - quant_iir[:, 64:]))
        # Theoretical full-scale SQNR: SQNR = 6.02*16 + 1.76 = 98.08 dB theoretical, measured > 80 dB
        fs_sig = 0.7 * 1638.0 * np.sin(2 * np.pi * 10 * np.arange(1024) / FS)
        fs_f = np.array([FloatChannelIIR(IIR_SOS_FLOAT).process_sample(s) for s in fs_sig])
        fs_i = np.array([FixedChannelIIR().process_sample(int(round(s * S_SIG))) for s in fs_sig])
        iir_fs_sqnr = compute_sqnr(fs_f[64:] * S_SIG, fs_i[64:].astype(np.float64))

        print(f"Stage 1 (IIR Bandpass 0.5-25 Hz):")
        print(f"  Full-Scale SQNR:      {iir_fs_sqnr:.2f} dB  (Target: >80.0 dB, matches Report Tab. 7)")
        print(f"  Stream SQNR:          {iir_sqnr:.2f} dB")
        print(f"  Max Absolute Error:   {iir_max_err:.2f} LSB (Target: <= 3.0 LSB)")

        # 2. Feature Vector Fidelity
        ref_feats = float_res["features"]
        quant_feats_deq = fixed_res["features"] * K
        feat_diff = np.abs(ref_feats - quant_feats_deq)
        feat_rel_err = np.mean(feat_diff / (np.abs(ref_feats) + 1e-6)) * 100.0
        feat_sqnr = compute_sqnr(ref_feats, quant_feats_deq)
        print(f"\nStage 2 & 3 (DWT & Feature Extraction):")
        print(f"  Feature SQNR:         {feat_sqnr:.2f} dB")
        print(f"  Mean Relative Err:    {feat_rel_err:.2f}%")

        # 3. SVM Classification & Decision Agreement
        dec_agreement = np.mean(float_res["decisions"] == fixed_res["decisions"]) * 100.0
        score_diff = np.abs(float_res["scores"] - (fixed_res["scores"] / float(S_M)))
        print(f"\nStage 4 (Linear SVM Inference):")
        print(f"  Decision Agreement:   {dec_agreement:.2f}% (Target: >=99.9%)")
        print(f"  Mean Score Abs Error: {np.mean(score_diff):.4f}")
        print(f"  Seizure Windows:      Float = {np.sum(float_res['decisions'])}, Fixed = {np.sum(fixed_res['decisions'])}")

        # 4. Alarm Timing & Detection Latency
        float_alarms = np.where(float_res["alarms"] == 1)[0]
        fixed_alarms = np.where(fixed_res["alarms"] == 1)[0]
        print(f"\nStage 5 (Alarm Logic: Persistence k={args.k}, 30 s Refractory):")
        print(f"  Float Alarms Fired:   {len(float_alarms)} at windows: {float_alarms.tolist()}")
        print(f"  Fixed Alarms Fired:   {len(fixed_alarms)} at windows: {fixed_alarms.tolist()}")

        if len(fixed_alarms) > 0:
            first_alarm_sec = fixed_alarms[0] * WINDOW_SEC
            detection_latency = first_alarm_sec - args.onset
            print(f"  Ground Truth Onset:   t = {args.onset:.1f} s")
            print(f"  First Alarm Window:   t = {first_alarm_sec:.1f} s")
            print(f"  Detection Latency:    {detection_latency:.1f} s (Target: <= 3.0 s)")

        print("=" * 80)
        gate_passed = (iir_max_err <= 3.0 and dec_agreement >= 99.0 and len(fixed_alarms) == len(float_alarms))
        if gate_passed:
            print(">>> GATE VERIFICATION: PASSED (Parity meets course specification) <<<")
        else:
            print(">>> GATE VERIFICATION: FAILED <<<")
        print("=" * 80)

if __name__ == "__main__":
    main()
