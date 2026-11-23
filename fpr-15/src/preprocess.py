"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: EEG file preprocessing, 22-channel extraction, 2s/1s windowing, 50% overlap labeling, and sanity plotting.
AI-assisted: yes
"""

import sys
import ast
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJ_ROOT))

from src.config import (
    FS,
    WINDOW_SEC,
    HOP_SEC,
    WINDOW_SAMPLES,
    HOP_SAMPLES,
    LABEL_OVERLAP_THRESH,
    ACTIVE_CHANNELS,
    MANIFEST_PATH,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    RESULTS_DIR
)
from src.data_io import read_edf

def compute_window_labels(num_samples: int, seizure_intervals: list) -> tuple:
    """
    Computes window start sample indices and binary labels.
    Window is positive (1) if >= 50% of the window lies inside an annotated seizure.
    Windows do NOT cross file boundaries.
    """
    window_starts = []
    window_labels = []

    # Number of possible full windows
    if num_samples < WINDOW_SAMPLES:
        return np.array([], dtype=np.int32), np.array([], dtype=np.int32)

    starts = np.arange(0, num_samples - WINDOW_SAMPLES + 1, HOP_SAMPLES, dtype=np.int32)

    for start_samp in starts:
        w_start_sec = start_samp / FS
        w_end_sec = (start_samp + WINDOW_SAMPLES) / FS
        w_dur = WINDOW_SEC

        # Calculate max overlap with any seizure interval
        max_overlap_sec = 0.0
        for sz_start, sz_end in seizure_intervals:
            overlap_start = max(w_start_sec, sz_start)
            overlap_end = min(w_end_sec, sz_end)
            if overlap_end > overlap_start:
                max_overlap_sec += (overlap_end - overlap_start)

        is_positive = 1 if (max_overlap_sec / w_dur) >= LABEL_OVERLAP_THRESH else 0
        window_starts.append(start_samp)
        window_labels.append(is_positive)

    return np.array(window_starts, dtype=np.int32), np.array(window_labels, dtype=np.int32)


def process_record(subject: str, filename: str, seizure_intervals: list):
    """
    Reads an EDF file, extracts signals on active channels, computes window labels,
    and saves to a compressed .npz archive in data/processed/.
    """
    edf_path = RAW_DATA_DIR / subject / filename
    if not edf_path.exists():
        raise FileNotFoundError(f"EDF file not found: {edf_path}")

    signals, info = read_edf(edf_path, active_channels=ACTIVE_CHANNELS)
    num_samples = info["num_samples"]

    window_starts, window_labels = compute_window_labels(num_samples, seizure_intervals)

    out_name = f"{subject}_{Path(filename).stem}.npz"
    out_path = PROCESSED_DATA_DIR / out_name

    np.savez_compressed(
        out_path,
        signals=signals,
        window_starts=window_starts,
        window_labels=window_labels,
        seizure_intervals=np.array(seizure_intervals, dtype=np.float32),
        fs=FS,
        num_channels=len(ACTIVE_CHANNELS),
        subject=subject,
        filename=filename,
        duration_sec=info["duration_sec"]
    )

    pos_count = int(np.sum(window_labels))
    total_w = len(window_labels)
    return {
        "subject": subject,
        "filename": filename,
        "processed_path": str(out_path),
        "num_windows": total_w,
        "positive_windows": pos_count,
        "negative_windows": total_w - pos_count,
        "duration_sec": info["duration_sec"]
    }


def generate_sanity_plot(subject: str, filename: str, seizure_intervals: list):
    """
    Generates a sanity plot of raw EEG around a seizure event with the annotated onset and offset.
    Saves the figure to results/seizure_onset_validation.png.
    """
    edf_path = RAW_DATA_DIR / subject / filename
    if not edf_path.exists() or not seizure_intervals:
        return

    signals, info = read_edf(edf_path, active_channels=ACTIVE_CHANNELS)
    sz_start, sz_end = seizure_intervals[0]

    # Plot 30s before and 30s after seizure
    t_start = max(0, sz_start - 30)
    t_end = min(info["duration_sec"], sz_end + 30)
    idx_start = int(t_start * FS)
    idx_end = int(t_end * FS)

    time_vec = np.linspace(t_start, t_end, idx_end - idx_start)
    
    # Plot first 6 channels for clarity
    num_plot_ch = min(6, len(ACTIVE_CHANNELS))
    fig, axes = plt.subplots(num_plot_ch, 1, figsize=(12, 8), sharex=True)
    if num_plot_ch == 1:
        axes = [axes]

    for i in range(num_plot_ch):
        ch_signal = signals[i, idx_start:idx_end]
        axes[i].plot(time_vec, ch_signal, color="#1f77b4", lw=0.8)
        axes[i].set_ylabel(ACTIVE_CHANNELS[i], fontsize=9)
        axes[i].grid(True, alpha=0.3)
        # Highlight annotated seizure region
        axes[i].axvspan(sz_start, sz_end, color="red", alpha=0.2, label="Annotated Seizure" if i == 0 else "")

    axes[0].legend(loc="upper right")
    axes[-1].set_xlabel("Time (seconds)", fontsize=11)
    fig.suptitle(f"Seizure Onset Validation ({subject} - {filename}): [{sz_start}s to {sz_end}s]", fontsize=13, fontweight="bold")
    plt.tight_layout()

    out_fig = RESULTS_DIR / "seizure_onset_validation.png"
    plt.savefig(out_fig, dpi=200)
    plt.close()
    print(f"[PLOT] Sanity verification plot saved to {out_fig}")


def main():
    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    df = pd.read_csv(MANIFEST_PATH)
    print(f"Processing available records from {MANIFEST_PATH}...")

    processed_summary = []
    plot_generated = False

    for _, row in df.iterrows():
        sub = row["subject"]
        fname = row["filename"]
        sz_intervals = ast.literal_eval(row["seizure_intervals"])
        raw_file = RAW_DATA_DIR / sub / fname

        if not raw_file.exists():
            continue

        res = process_record(sub, fname, sz_intervals)
        processed_summary.append(res)
        print(f"[PROCESSED] {sub}/{fname}: {res['num_windows']} windows ({res['positive_windows']} positive)")

        if not plot_generated and len(sz_intervals) > 0:
            generate_sanity_plot(sub, fname, sz_intervals)
            plot_generated = True

    if processed_summary:
        summary_df = pd.DataFrame(processed_summary)
        summary_df.to_csv(RESULTS_DIR / "preprocessing_summary.csv", index=False)
        print(f"\nPreprocessing complete: {len(processed_summary)} files processed.")
    else:
        print("No raw EDF files found on disk yet. Download files first.")

if __name__ == "__main__":
    main()
