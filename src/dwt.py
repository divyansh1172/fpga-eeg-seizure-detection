"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Causal IIR band-pass filter (0.5-25 Hz SOS) and 5-level Daubechies-4 (db4) Discrete Wavelet Transform.
         Includes Stage A (window-based pywt) and Stage B (streaming causal direct-form filter bank).
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np
import scipy.signal as signal
import pywt

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    FS,
    BANDPASS_LOW_HZ,
    BANDPASS_HIGH_HZ,
    WAVELET_NAME,
    DWT_LEVEL,
    BASELINE_BANDS
)

def create_causal_bandpass_filter(fs: int = FS, low_hz: float = BANDPASS_LOW_HZ, high_hz: float = BANDPASS_HIGH_HZ, order: int = 2):
    """
    Creates Second-Order Sections (SOS) for causal Butterworth band-pass filter.
    order=2 gives a 4th-order filter (cascade of 2 biquads).
    """
    sos = signal.butter(
        order,
        [low_hz, high_hz],
        btype="bandpass",
        fs=fs,
        output="sos"
    )
    return sos


def apply_causal_bandpass(signals: np.ndarray, sos: np.ndarray) -> np.ndarray:
    """
    Applies causal IIR filtering along time axis using sosfilt (forward only, no lookahead).
    Input shape: (num_channels, num_samples)
    Output shape: (num_channels, num_samples)
    """
    filtered = signal.sosfilt(sos, signals, axis=1)
    return filtered.astype(np.float32)


def compute_dwt_stage_a(window_signal: np.ndarray, wavelet_name: str = WAVELET_NAME, level: int = DWT_LEVEL) -> dict:
    """
    Stage A (reference): Computes 5-level DWT per window using PyWavelets.
    Mode 'periodization' ensures exact dyadic lengths matching multiresolution dyadic trees.
    For a 2s window (512 samples):
        D1: 256 samples
        D2: 128 samples
        D3: 64 samples
        D4: 32 samples
        D5: 16 samples
        A5: 16 samples
    Returns dict mapping band name ('D1', ..., 'D5', 'A5') -> 1D numpy array.
    """
    coeffs = pywt.wavedec(window_signal, wavelet_name, level=level, mode="periodization")
    # pywt.wavedec returns: [cA5, cD5, cD4, cD3, cD2, cD1]
    subbands = {
        "A5": coeffs[0],
        "D5": coeffs[1],
        "D4": coeffs[2],
        "D3": coeffs[3],
        "D2": coeffs[4],
        "D1": coeffs[5]
    }
    return subbands


# Daubechies 4 (db4) exact 8-tap filter coefficients
DB4_WAVELET = pywt.Wavelet("db4")
H_LOW = np.array(DB4_WAVELET.dec_lo, dtype=np.float32)   # 8 lowpass decomposition taps
G_HIGH = np.array(DB4_WAVELET.dec_hi, dtype=np.float32)  # 8 highpass decomposition taps

def streaming_dwt_1level(x: np.ndarray, h: np.ndarray = H_LOW, g: np.ndarray = G_HIGH) -> tuple:
    """
    Single-level causal analysis filter pair with downsampling by 2.
    Direct-form FIR convolution followed by decimation.
    """
    # Convolve with causal zero-padding
    low_out = np.convolve(x, h, mode="full")[:len(x) + len(h) - 1]
    high_out = np.convolve(x, g, mode="full")[:len(x) + len(g) - 1]

    # Downsample by 2
    approx = low_out[len(h)-1::2]
    detail = high_out[len(g)-1::2]
    return approx, detail


def compute_dwt_stage_b(window_signal: np.ndarray, level: int = DWT_LEVEL) -> dict:
    """
    Stage B (streaming/hardware matching): Computes J levels of direct-form FIR + decimation.
    """
    current_a = window_signal.copy()
    subbands = {}

    for j in range(1, level + 1):
        approx, detail = streaming_dwt_1level(current_a, H_LOW, G_HIGH)
        subbands[f"D{j}"] = detail
        current_a = approx

    subbands[f"A{level}"] = current_a
    return subbands


def cross_check_stages(window_signal: np.ndarray) -> float:
    """
    Cross-checks Stage B against Stage A on interior samples to verify equivalence.
    Returns maximum relative error on interior coefficients of retained bands.
    """
    res_a = compute_dwt_stage_a(window_signal)
    res_b = compute_dwt_stage_b(window_signal)

    max_err = 0.0
    for band in BASELINE_BANDS:
        a_coeff = res_a[band]
        b_coeff = res_b[band]
        # Align interior samples (ignoring boundary filter warmup of 7 samples)
        min_len = min(len(a_coeff), len(b_coeff))
        if min_len > 10:
            diff = np.abs(a_coeff[4:min_len-4] - b_coeff[4:min_len-4])
            denom = np.abs(a_coeff[4:min_len-4]) + 1e-6
            rel_err = np.max(diff / denom)
            max_err = max(max_err, rel_err)

    return float(max_err)
