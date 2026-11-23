"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Wavelet-domain feature extraction: sub-band energy (E) and line-length (LL).
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    BASELINE_BANDS,
    NUM_CHANNELS,
    ACTIVE_CHANNELS
)
from src.dwt import compute_dwt_stage_a

def extract_subband_features(coefficients: np.ndarray, include_log: bool = False) -> list:
    """
    Computes energy (E) and line-length (LL) for a 1D coefficient vector.
    E  = (1 / Nb) * sum(c_i^2)
    LL = (1 / (Nb - 1)) * sum(|c_i - c_{i-1}|)
    """
    nb = len(coefficients)
    if nb == 0:
        return [0.0, 0.0]

    # Sub-band Energy
    energy = float(np.mean(coefficients ** 2))

    # Line-Length
    if nb > 1:
        line_length = float(np.mean(np.abs(np.diff(coefficients))))
    else:
        line_length = 0.0

    feats = [energy, line_length]
    if include_log:
        feats.append(float(np.log(energy + 1e-8)))

    return feats


def extract_window_features(
    window_signals: np.ndarray,
    bands: list = BASELINE_BANDS,
    include_log: bool = False,
    feature_set: str = "all"  # 'all' (E+LL), 'energy' (E only), 'linelength' (LL only)
) -> np.ndarray:
    """
    Extracts features for a single 2s multi-channel window.
    window_signals shape: (num_channels, window_samples)
    Returns: 1D feature vector of shape (D,)
    """
    n_channels = window_signals.shape[0]
    all_features = []

    for ch_idx in range(n_channels):
        sig = window_signals[ch_idx]
        subbands = compute_dwt_stage_a(sig)

        for b in bands:
            coeffs = subbands[b]
            feats = extract_subband_features(coeffs, include_log=(include_log or feature_set == "log_energy"))
            
            if feature_set == "energy":
                all_features.append(feats[0])
            elif feature_set == "linelength":
                all_features.append(feats[1])
            elif feature_set == "log_energy":
                all_features.append(np.log(feats[0] + 1e-8))
            else:  # 'all': E and LL
                all_features.extend(feats[:2])

    return np.array(all_features, dtype=np.float32)


def extract_record_features(
    signals: np.ndarray,
    window_starts: np.ndarray,
    window_samples: int,
    bands: list = BASELINE_BANDS,
    feature_set: str = "all"
) -> np.ndarray:
    """
    Extracts features for all windows in a continuous multi-channel recording.
    signals shape: (num_channels, num_samples)
    window_starts shape: (num_windows,)
    Returns: feature matrix of shape (num_windows, feature_dim)
    """
    num_windows = len(window_starts)
    if num_windows == 0:
        return np.empty((0, 0), dtype=np.float32)

    features_list = []
    for start_samp in window_starts:
        win_sig = signals[:, start_samp : start_samp + window_samples]
        feat_vec = extract_window_features(win_sig, bands=bands, feature_set=feature_set)
        features_list.append(feat_vec)

    return np.array(features_list, dtype=np.float32)
