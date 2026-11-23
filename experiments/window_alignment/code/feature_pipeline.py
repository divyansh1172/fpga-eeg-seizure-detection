"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.feature_pipeline
Purpose: Self-contained, deterministic signal preprocessing, 5-level Daubechies-4 (db4)
         DWT decomposition, and Energy + Line-Length feature extraction (176 features).
         Operates with pure NumPy/SciPy (no PyWavelets dependency required).
"""

from typing import List, Dict, Any, Tuple
import numpy as np
import scipy.signal as signal

# ==============================================================================
# Exact Daubechies-4 (db4) 8-Tap Decomposition Filter Coefficients
# Matching standard IEEE / PyWavelets / RTL coefficients
# ==============================================================================
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

RETAINED_BANDS = ["D3", "D4", "D5", "A5"]

def create_causal_bandpass_filter(fs: int = 256, low_hz: float = 0.5, high_hz: float = 25.0, order: int = 2) -> np.ndarray:
    """
    Creates Second-Order Sections (SOS) for causal Butterworth bandpass filter.
    order=2 produces a 4th-order filter (two cascaded biquads).
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
    Applies causal IIR filtering along time axis using forward-only sosfilt.
    signals shape: (num_channels, num_samples)
    """
    filtered = signal.sosfilt(sos, signals, axis=1)
    return filtered.astype(np.float32)

def compute_dwt_5levels_1d(x: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Computes 5-level Daubechies-4 DWT decomposition for a 1D signal window
    using periodization mode / causal downsampled convolution matching dyadic trees.
    Returns: dict mapping 'D1', 'D2', 'D3', 'D4', 'D5', 'A5' -> 1D arrays of coefficients.
    """
    subbands: Dict[str, np.ndarray] = {}
    current_approx = np.asarray(x, dtype=np.float64)
    
    h_len = len(DB4_DEC_LO)  # 8
    
    for level in range(1, 6):
        n_in = len(current_approx)
        
        # Periodized extension to ensure exact dyadic power-of-two lengths
        pad_len = h_len - 1
        # Circular padding
        if n_in >= pad_len:
            x_pad = np.concatenate([current_approx, current_approx[:pad_len]])
        else:
            repeats = (pad_len // n_in) + 2
            x_pad = np.tile(current_approx, repeats)[:n_in + pad_len]
            
        conv_lo = np.convolve(x_pad, DB4_DEC_LO, mode="valid")
        conv_hi = np.convolve(x_pad, DB4_DEC_HI, mode="valid")
        
        # Downsample by 2
        approx = conv_lo[::2][:n_in // 2]
        detail = conv_hi[::2][:n_in // 2]
        
        subbands[f"D{level}"] = detail.astype(np.float32)
        current_approx = approx
        
    subbands["A5"] = current_approx.astype(np.float32)
    return subbands

def extract_subband_features(coefficients: np.ndarray) -> Tuple[float, float]:
    """
    Computes mean Energy and Line-Length for a 1D coefficient vector:
        Energy = (1 / Nb) * sum(c[n]^2)
        LineLength = (1 / (Nb - 1)) * sum(|c[n] - c[n-1]|)
    """
    nb = len(coefficients)
    if nb == 0:
        return 0.0, 0.0
        
    energy = float(np.mean(coefficients ** 2))
    
    if nb > 1:
        line_length = float(np.mean(np.abs(np.diff(coefficients))))
    else:
        line_length = 0.0
        
    return energy, line_length

def extract_window_features_176(
    window_signals: np.ndarray,
    retained_bands: List[str] = RETAINED_BANDS
) -> np.ndarray:
    """
    Extracts 176 features from a multi-channel window (22 channels).
    Ordering: Channel-major (0..21), Subband-major (D3, D4, D5, A5), Feature-minor (Energy, Line-Length).
    window_signals shape: (22, window_samples)
    Returns: 1D feature array of shape (176,) in float32.
    """
    num_channels = window_signals.shape[0]
    features: List[float] = []
    
    for ch in range(num_channels):
        sig = window_signals[ch]
        subbands = compute_dwt_5levels_1d(sig)
        
        for b in retained_bands:
            coeffs = subbands[b]
            e, ll = extract_subband_features(coeffs)
            features.extend([e, ll])
            
    return np.array(features, dtype=np.float32)

def generate_window_slices(
    num_samples: int,
    window_samples: int,
    hop_samples: int,
    fs: int = 256,
    seizure_intervals: Optional[List[Tuple[float, float]]] = None,
    label_overlap_thresh: float = 0.5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates window slice start sample indices, start timestamps in seconds,
    and binary ground-truth labels.
    A window is labelled positive (1) if >= label_overlap_thresh of its duration
    lies inside an annotated seizure interval.
    Windows do NOT cross file boundaries.
    """
    if num_samples < window_samples:
        return np.array([], dtype=np.int32), np.array([], dtype=np.float32), np.array([], dtype=np.int32)
        
    starts_sample = np.arange(0, num_samples - window_samples + 1, hop_samples, dtype=np.int32)
    starts_sec = starts_sample / float(fs)
    w_dur_sec = window_samples / float(fs)
    
    labels: List[int] = []
    intervals = seizure_intervals or []
    
    for s_sec in starts_sec:
        w_end_sec = s_sec + w_dur_sec
        overlap_sec = 0.0
        for sz_start, sz_end in intervals:
            o_start = max(s_sec, sz_start)
            o_end = min(w_end_sec, sz_end)
            if o_end > o_start:
                overlap_sec += (o_end - o_start)
                
        is_pos = 1 if (overlap_sec / w_dur_sec) >= label_overlap_thresh else 0
        labels.append(is_pos)
        
    return starts_sample, starts_sec.astype(np.float32), np.array(labels, dtype=np.int32)
