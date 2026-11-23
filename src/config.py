"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Central configuration freezing all experiment parameters, paths, and protocol settings.
AI-assisted: yes
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MANIFEST_PATH = DATA_DIR / "manifest.csv"
RESULTS_DIR = BASE_DIR / "results"
VECTORS_DIR = BASE_DIR / "vectors"
REPORT_DIR = BASE_DIR / "report"

for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, RESULTS_DIR, VECTORS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Random Seed for reproducibility
RANDOM_SEED = 42

# Signal Acquisition / Sampling
FS = 256  # Sampling frequency (Hz)

# Subjects (frozen per protocol: first 3 cases with >= 3 seizures and common 23-ch montage)
SUBJECTS = ["chb01", "chb02", "chb03"]

# Channel Definition
# Standard 23-entry bipolar montage from CHB-MIT summary files
# Note: In the raw summaries, entry 15 and 23 are both named 'T8-P8'.
# Duplicate T8-P8 is dropped per plan (Line 660), giving 22 unique bipolar channels,
# or kept as 23 channels if retaining raw index.
# We define the unique 22 bipolar channels in fixed order:
CHANNELS_22 = [
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1",
    "FP1-F3", "F3-C3", "C3-P3", "P3-O1",
    "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
    "FP2-F8", "F8-T8", "T8-P8", "P8-O2",
    "FZ-CZ", "CZ-PZ", "P7-T7", "T7-FT9",
    "FT9-FT10", "FT10-T8"
]

# Raw 23 channels before deduplication
CHANNELS_23_RAW = [
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1",
    "FP1-F3", "F3-C3", "C3-P3", "P3-O1",
    "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
    "FP2-F8", "F8-T8", "T8-P8", "P8-O2",
    "FZ-CZ", "CZ-PZ", "P7-T7", "T7-FT9",
    "FT9-FT10", "FT10-T8", "T8-P8"
]

# Active channel set used in baseline (22 unique bipolar channels)
ACTIVE_CHANNELS = CHANNELS_22
NUM_CHANNELS = len(ACTIVE_CHANNELS)

# Windowing and Hop
WINDOW_SEC = 2.0
HOP_SEC = 1.0
WINDOW_SAMPLES = int(WINDOW_SEC * FS)  # 512
HOP_SAMPLES = int(HOP_SEC * FS)        # 256

# Labeling Rule
LABEL_OVERLAP_THRESH = 0.5  # Window positive if >= 50% inside annotated seizure

# Preprocessing / Filtering
BANDPASS_LOW_HZ = 0.5
BANDPASS_HIGH_HZ = 25.0
IIR_ORDER = 2  # 2nd-order biquad section (or 4th order cascade)

# Wavelet Decomposition
WAVELET_NAME = "db4"
DWT_LEVEL = 5
# At 256 Hz:
# D1: 64-128 Hz (drop)
# D2: 32-64 Hz (drop in baseline; ablate in S6)
# D3: 16-32 Hz (keep)
# D4: 8-16 Hz (keep)
# D5: 4-8 Hz (keep)
# A5: 0-4 Hz (keep)
BASELINE_BANDS = ["D3", "D4", "D5", "A5"]

# Features per retained sub-band: Sub-band Energy (E) and Line-Length (LL)
NUM_FEATURES_PER_BAND = 2  # E and LL
FEATURE_DIM = NUM_CHANNELS * len(BASELINE_BANDS) * NUM_FEATURES_PER_BAND  # 22 * 4 * 2 = 176

# Post-processing and Alarm Logic
K_CONSECUTIVE = 3  # Trigger alarm after k consecutive positive windows
EVENT_TOLERANCE_SEC = 2.0  # Tol = 2 s: detection valid if alarm in [onset - tol, end]
EVENT_REFRACTORY_SEC = 30.0  # Refractory period: merge alarms within 30 s

# Classifier
SVM_C = 1.0
SVM_CLASS_WEIGHT = "balanced"
SVM_MAX_ITER = 20000

# Hardware Specs for Reference
DSP_MAX_SLICES = 120
BRAM_MAX_KB = 337
UART_BAUD = 230400
