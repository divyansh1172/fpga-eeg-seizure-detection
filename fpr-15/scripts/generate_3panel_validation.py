"""
Generate 3-Panel Seizure Onset Validation Figure using saved model.
Panel 1 (Top): 6 Raw EEG Channels (pre-seizure and ictal spike-wave discharges).
Panel 2 (Middle): Normalized DWT Sub-band Features (Energy & Line-Length).
Panel 3 (Bottom): Streaming Linear SVM Decision Score & Alarm Trigger (k=3).
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.config import FS, ACTIVE_CHANNELS, RESULTS_DIR, PROCESSED_DATA_DIR, WINDOW_SAMPLES, HOP_SAMPLES
from src.dwt import create_causal_bandpass_filter, apply_causal_bandpass
from src.features import extract_window_features

def main():
    target_rec = "chb01_03.edf"
    npz_path = PROCESSED_DATA_DIR / "chb01_chb01_03.npz"
    model_path = RESULTS_DIR / "models" / "chb01_fold0_model.pkl"
    
    print(f"Loading cached record {npz_path.name}...")
    d = np.load(npz_path, allow_pickle=True)
    raw_signals = d["signals"]
    seizure_intervals = d["seizure_intervals"].tolist()
    sz_start, sz_end = seizure_intervals[0] # (2996, 3036)
    
    print(f"Loading trained SVM model from {model_path.name}...")
    with open(model_path, "rb") as f:
        model_dict = pickle.load(f)
    clf = model_dict["clf"]
    scaler = model_dict["scaler"]
    
    # We will analyze from 2960s to 3050s (90 seconds total)
    plot_t_start = 2960
    plot_t_end = 3050
    
    sos = create_causal_bandpass_filter()
    filt_signals = apply_causal_bandpass(raw_signals, sos)
    
    # Window step is 1.0s, window size is 2.0s
    # Extract features for all windows in the region
    w_starts = np.arange(plot_t_start, plot_t_end - 2, 1)
    feats_list = []
    
    for ws in w_starts:
        idx_s = int(ws * FS)
        idx_e = idx_s + WINDOW_SAMPLES
        win_sig = filt_signals[:, idx_s:idx_e]
        f = extract_window_features(win_sig, bands=["D3", "D4", "D5", "A5"], feature_set="all")
        feats_list.append(f)
        
    feats_array = np.array(feats_list)
    feats_scaled = scaler.transform(feats_array)
    svm_scores = clf.decision_function(feats_scaled)
    
    # Evaluate alarm assertion (k=3 consecutive windows)
    consec = 0
    alarm_time = None
    k = 3
    for t, s in zip(w_starts, svm_scores):
        if s > 0:
            consec += 1
            if consec == k and alarm_time is None:
                alarm_time = t
        else:
            consec = 0
            
    latency = (alarm_time - sz_start) if alarm_time else None
    print(f"Seizure onset: {sz_start}s, Alarm assertion: {alarm_time}s, Latency: {latency}s")
    
    # --- Create Publication-Quality 3-Panel Figure ---
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True, gridspec_kw={'height_ratios': [2.2, 1.2, 1.2]})
    
    # Panel 1: 6 Representative Bipolar Channels
    ch_indices = [0, 4, 8, 12, 16, 17] # Frontal, central, parietal, occipital
    ch_labels = [ACTIVE_CHANNELS[c] for c in ch_indices]
    spacing = 160.0
    
    idx_raw_start = int(plot_t_start * FS)
    idx_raw_end = int(plot_t_end * FS)
    time_raw = np.linspace(plot_t_start, plot_t_end, idx_raw_end - idx_raw_start)
    
    for i, (c_idx, name) in enumerate(zip(ch_indices, ch_labels)):
        sig = raw_signals[c_idx, idx_raw_start:idx_raw_end]
        offset = (len(ch_indices) - 1 - i) * spacing
        axes[0].plot(time_raw, sig + offset, color="#1f77b4", lw=0.7)
        axes[0].text(plot_t_start - 1.2, offset, name, fontsize=8, verticalalignment='center', fontweight='bold', color="#222222")
        
    axes[0].axvspan(sz_start, sz_end, color="crimson", alpha=0.15, label=f"Annotated Seizure ({sz_start}s to {sz_end}s)")
    axes[0].axvline(sz_start, color="crimson", linestyle="--", lw=1.5, label="Clinical Onset ($t=2996$s)")
    axes[0].set_ylim(-spacing * 0.7, len(ch_indices) * spacing)
    axes[0].set_yticks([])
    axes[0].set_ylabel("Raw Bipolar EEG (μV)", fontsize=10, fontweight='bold')
    axes[0].set_title("Seizure Onset Temporal Validation & Real-Time Alarm Dynamics (Subject chb01, Record chb01_03.edf)", fontsize=11, fontweight='bold')
    axes[0].legend(loc="upper left", framealpha=0.9, fontsize=9)
    axes[0].grid(True, alpha=0.25)
    
    # Panel 2: Normalized DWT Features
    # Energy features are even columns, Line-length are odd columns
    energy_features = feats_array[:, 0::2]
    ll_features = feats_array[:, 1::2]
    
    mean_energy = np.mean(energy_features, axis=1)
    mean_ll = np.mean(ll_features, axis=1)
    
    # Normalize to [0, 1]
    norm_energy = (mean_energy - mean_energy.min()) / (mean_energy.max() - mean_energy.min() + 1e-6)
    norm_ll = (mean_ll - mean_ll.min()) / (mean_ll.max() - mean_ll.min() + 1e-6)
    
    axes[1].plot(w_starts, norm_energy, marker='o', markersize=3, color="#2ca02c", lw=1.5, label="Mean DWT Energy (Normalized)")
    axes[1].plot(w_starts, norm_ll, marker='s', markersize=3, color="#ff7f0e", lw=1.5, label="Mean Line-Length (Normalized)")
    axes[1].axvspan(sz_start, sz_end, color="crimson", alpha=0.15)
    axes[1].axvline(sz_start, color="crimson", linestyle="--", lw=1.5)
    axes[1].set_ylabel("DWT Features", fontsize=10, fontweight='bold')
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].legend(loc="upper left", framealpha=0.9, fontsize=9)
    axes[1].grid(True, alpha=0.25)
    
    # Panel 3: SVM Score and Alarm Trigger
    axes[2].plot(w_starts, svm_scores, marker='d', markersize=4, color="#1f77b4", lw=1.8, label="Linear SVM Decision Score $y(t) = \mathbf{w}^\\top \mathbf{x} + b$")
    axes[2].axhline(0, color="black", linestyle="--", lw=1.2, label="Decision Threshold ($y=0$)")
    axes[2].axvspan(sz_start, sz_end, color="crimson", alpha=0.15)
    axes[2].axvline(sz_start, color="crimson", linestyle="--", lw=1.5)
    
    if alarm_time:
        axes[2].axvline(alarm_time, color="crimson", linestyle="-", lw=2.2, label=f"Alarm Assertion ($t={alarm_time:.0f}$s)")
        axes[2].annotate(
            f"ALARM (k=3)\n$t={alarm_time:.0f}$s (Latency $\\tau={alarm_time-sz_start:.0f}$s)",
            xy=(alarm_time, 0.5),
            xytext=(alarm_time + 4, 2.2),
            arrowprops=dict(facecolor='crimson', shrink=0.08, width=1.5, headwidth=6),
            fontsize=9, fontweight='bold', color="crimson",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="crimson", lw=1.5)
        )
        
    axes[2].set_ylabel("SVM Score", fontsize=10, fontweight='bold')
    axes[2].set_xlabel("Continuous Recording Time (seconds)", fontsize=10, fontweight='bold')
    axes[2].set_xlim(plot_t_start, plot_t_end)
    axes[2].legend(loc="upper left", framealpha=0.9, fontsize=9)
    axes[2].grid(True, alpha=0.25)
    
    plt.tight_layout()
    out_fig = RESULTS_DIR / "seizure_onset_validation.png"
    plt.savefig(out_fig, dpi=250)
    plt.close()
    print(f"[SUCCESS] 3-panel validation figure generated cleanly at {out_fig}")

if __name__ == "__main__":
    main()
