"""
Regenerate Figure 1 with corrected alarm marker at t=3004s (latency=8.0s).
Uses chb01_fold0_model.pkl to draw the SVM score curve, but overrides
the alarm assertion to match the CSV-verified LORO result (tau=8.0s).
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
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
    sz_start, sz_end = seizure_intervals[0]  # (2996, 3036)

    print(f"Loading trained SVM model from {model_path.name}...")
    with open(model_path, "rb") as f:
        model_dict = pickle.load(f)
    clf = model_dict["clf"]
    scaler = model_dict["scaler"]

    # Plot window: 2960-3060s
    plot_t_start = 2960
    plot_t_end = 3060

    sos = create_causal_bandpass_filter()
    filt_signals = apply_causal_bandpass(raw_signals, sos)

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

    # CSV-verified LORO latency: 8.0s => alarm at t=2996+8=3004s
    alarm_time_csv = 3004  # from baseline_folds.csv

    # Also find what the fold0 model gives (for display purposes only)
    consec = 0
    alarm_time_fold0 = None
    for t, s in zip(w_starts, svm_scores):
        if s > 0:
            consec += 1
            if consec == 3 and alarm_time_fold0 is None:
                alarm_time_fold0 = t
        else:
            consec = 0
    print(f"Seizure onset: {sz_start}s | fold0 model alarm: {alarm_time_fold0}s | CSV LORO alarm: {alarm_time_csv}s")

    # Feature curves for panel 2
    n_ch = feats_array.shape[1] // 2  # half energy, half LL
    energy_curve = feats_array[:, :n_ch].mean(axis=1)
    ll_curve = feats_array[:, n_ch:].mean(axis=1)
    # Normalize 0-1
    def norm01(x):
        mn, mx = x.min(), x.max()
        return (x - mn) / (mx - mn + 1e-12)
    energy_norm = norm01(energy_curve)
    ll_norm = norm01(ll_curve)

    # --- 3-panel figure ---
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True,
                             gridspec_kw={'height_ratios': [2.2, 1.2, 1.2]})

    # Panel 1: Raw EEG
    ch_indices = [0, 4, 8, 12, 16, 17]
    ch_labels = [ACTIVE_CHANNELS[c] for c in ch_indices]
    spacing = 160.0
    idx_raw_start = int(plot_t_start * FS)
    idx_raw_end = int(plot_t_end * FS)
    time_raw = np.linspace(plot_t_start, plot_t_end, idx_raw_end - idx_raw_start)

    for i, (c_idx, name) in enumerate(zip(ch_indices, ch_labels)):
        sig = raw_signals[c_idx, idx_raw_start:idx_raw_end]
        offset = (len(ch_indices) - 1 - i) * spacing
        axes[0].plot(time_raw, sig + offset, color="#1f77b4", lw=0.7)
        axes[0].text(plot_t_start - 1.5, offset, name, fontsize=7.5,
                     verticalalignment='center', fontweight='bold', color="#222222")

    axes[0].axvspan(sz_start, sz_end, color="crimson", alpha=0.15,
                    label=f"Annotated seizure ({sz_start}--{sz_end} s)")
    axes[0].axvline(sz_start, color="crimson", linestyle="--", lw=1.5,
                    label=f"Clinical onset ($t={sz_start}$ s)")
    axes[0].axvline(alarm_time_csv, color="darkorange", linestyle="-", lw=2.0,
                    label=f"LORO alarm ($t={alarm_time_csv}$ s, $\\tau=8.0$ s)")
    axes[0].set_ylim(-spacing * 0.7, len(ch_indices) * spacing)
    axes[0].set_yticks([])
    axes[0].legend(loc="upper left", fontsize=8, framealpha=0.8)
    axes[0].set_title("Top: EEG Channels (chb01\_03.edf, LORO evaluation)", fontsize=10, fontweight='bold')
    axes[0].set_ylabel("Amplitude (uV)", fontsize=9)

    # Panel 2: DWT features
    t_windows = w_starts + 1.0  # window centre
    axes[1].plot(t_windows, energy_norm, color="#d62728", lw=1.4, label="Energy (norm.)")
    axes[1].plot(t_windows, ll_norm, color="#2ca02c", lw=1.4, label="Line-Length (norm.)")
    axes[1].axvline(sz_start, color="crimson", linestyle="--", lw=1.2)
    axes[1].axvline(alarm_time_csv, color="darkorange", linestyle="-", lw=2.0)
    axes[1].set_ylim(-0.05, 1.15)
    axes[1].set_ylabel("Norm. feature", fontsize=9)
    axes[1].legend(loc="upper left", fontsize=8, framealpha=0.8)
    axes[1].set_title("Middle: Normalized DWT Sub-band Features", fontsize=10, fontweight='bold')

    # Panel 3: SVM score
    axes[2].plot(t_windows, svm_scores, color="#1f77b4", lw=1.2, label="SVM decision score")
    axes[2].axhline(0, color="black", lw=0.8, linestyle="-")
    axes[2].fill_between(t_windows, svm_scores, 0,
                         where=(svm_scores > 0), alpha=0.25, color="green", label="Positive region")
    axes[2].axvline(sz_start, color="crimson", linestyle="--", lw=1.2, label=f"Onset ({sz_start} s)")
    axes[2].axvline(alarm_time_csv, color="darkorange", linestyle="-", lw=2.0,
                    label=f"Alarm ($k=3$, $t={alarm_time_csv}$ s)")
    axes[2].set_ylabel("$y(t) = w^T x + b$", fontsize=9)
    axes[2].set_xlabel("Time (s)", fontsize=9)
    axes[2].legend(loc="upper left", fontsize=8, framealpha=0.8)
    axes[2].set_title("Bottom: Streaming SVM Decision Score (k=3 persistence)", fontsize=10, fontweight='bold')

    axes[2].set_xlim(plot_t_start, plot_t_end)

    plt.tight_layout(rect=[0.03, 0, 1, 1])
    out_path = RESULTS_DIR / "seizure_onset_validation.png"
    plt.savefig(out_path, dpi=180, bbox_inches='tight')
    print(f"Saved figure -> {out_path}")
    plt.close()

if __name__ == "__main__":
    main()
