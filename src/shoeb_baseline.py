"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Replication of Shoeb & Guttag (ICML 2010) baseline:
         8-band filter-bank energy features (0.5-25 Hz), 3-window temporal stacking, and RBF-SVM.
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np
import scipy.signal as signal
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    FS,
    SUBJECTS,
    PROCESSED_DATA_DIR,
    RESULTS_DIR,
    RANDOM_SEED,
    WINDOW_SAMPLES,
    K_CONSECUTIVE
)
from src.postprocess import apply_k_consecutive_alarm
from src.evaluate import score_record_events, aggregate_subject_metrics
from src.train import load_record_data

# 8 Band-pass filter edges spanning 0.5 - 25 Hz (each ~3 Hz wide)
SHOEB_BANDS = [
    (0.5, 3.5),
    (3.5, 6.5),
    (6.5, 9.5),
    (9.5, 12.5),
    (12.5, 15.5),
    (15.5, 18.5),
    (18.5, 21.5),
    (21.5, 25.0)
]

def extract_shoeb_filterbank_features(signals: np.ndarray, window_starts: np.ndarray) -> np.ndarray:
    """
    Extracts 8-band energy features per channel for each 2s window.
    Features per window: 22 channels * 8 bands = 176 features.
    Then stacks 3 consecutive windows (t-2, t-1, t) -> 528 features per decision.
    """
    num_channels, num_samples = signals.shape
    num_windows = len(window_starts)
    if num_windows == 0:
        return np.empty((0, 0), dtype=np.float32)

    # Filter signals into 8 bands
    band_energies = np.zeros((num_windows, num_channels, len(SHOEB_BANDS)), dtype=np.float32)

    for b_idx, (low, high) in enumerate(SHOEB_BANDS):
        sos = signal.butter(2, [low, high], btype="bandpass", fs=FS, output="sos")
        filt_sig = signal.sosfilt(sos, signals, axis=1)

        for w_idx, start_samp in enumerate(window_starts):
            win = filt_sig[:, start_samp : start_samp + WINDOW_SAMPLES]
            # Energy = mean square per channel
            band_energies[w_idx, :, b_idx] = np.mean(win ** 2, axis=1)

    # Flatten spatial-spectral feature vector per window: (num_windows, 22 * 8 = 176)
    w_feats = band_energies.reshape(num_windows, -1)

    # Stack 3 consecutive windows (temporal stacking)
    # For window 0: repeat window 0; for window 1: repeat window 0, 1
    stacked_feats = np.zeros((num_windows, w_feats.shape[1] * 3), dtype=np.float32)
    for w_idx in range(num_windows):
        w0 = w_feats[max(0, w_idx - 2)]
        w1 = w_feats[max(0, w_idx - 1)]
        w2 = w_feats[w_idx]
        stacked_feats[w_idx] = np.concatenate([w0, w1, w2])

    return stacked_feats


def run_shoeb_replication_for_subject(subject: str):
    """
    Runs Shoeb-style RBF-SVM cross-validation under the exact same LORO split.
    """
    record_files = sorted(list(PROCESSED_DATA_DIR.glob(f"{subject}_*.npz")))
    if len(record_files) < 2:
        return [], {}

    print(f"\n--- Running Shoeb Replication (RBF-SVM) for {subject} ---")

    # Step 1: Pre-extract Shoeb features for all records of subject
    records_cache = []
    for fpath in record_files:
        rec = load_record_data(fpath)
        feats = extract_shoeb_filterbank_features(rec["signals"], rec["window_starts"])
        records_cache.append({
            "filename": rec["filename"],
            "features": feats,
            "window_starts": rec["window_starts"],
            "window_labels": rec["window_labels"],
            "seizure_intervals": rec["seizure_intervals"],
            "duration_sec": rec["duration_sec"]
        })

    # Step 2: LORO Loop with RBF-SVM
    fold_results = []
    subject_event_scores = []

    for test_idx, test_rec in enumerate(records_cache):
        test_fname = test_rec["filename"]

        train_x_list = [r["features"] for idx, r in enumerate(records_cache) if idx != test_idx]
        train_y_list = [r["window_labels"] for idx, r in enumerate(records_cache) if idx != test_idx]

        X_train = np.vstack(train_x_list)
        y_train = np.concatenate(train_y_list)
        X_test = test_rec["features"]
        y_test = test_rec["window_labels"]

        if np.sum(y_train) == 0:
            continue

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Shoeb RBF-SVM
        clf = SVC(
            kernel="rbf",
            class_weight="balanced",
            C=1.0,
            gamma="scale",
            random_state=RANDOM_SEED
        )
        clf.fit(X_train_scaled, y_train)

        y_pred = clf.predict(X_test_scaled)

        # Alarm logic (k=3 in a row)
        raw_alarms = apply_k_consecutive_alarm(y_pred, test_rec["window_starts"], k=K_CONSECUTIVE)

        # Event Scoring
        event_score = score_record_events(
            raw_alarms,
            test_rec["seizure_intervals"],
            test_rec["duration_sec"]
        )
        subject_event_scores.append(event_score)

        fold_results.append({
            "subject": subject,
            "held_out_record": test_fname,
            "detected_seizures": event_score["detected_seizures"],
            "total_seizures": event_score["num_seizures"],
            "false_alarms": event_score["false_alarms"],
            "non_seizure_hours": event_score["non_seizure_hours"],
            "latencies": str(event_score["latencies"])
        })

    summary = aggregate_subject_metrics(subject_event_scores)
    summary["subject"] = subject
    summary["model"] = "Shoeb_RBF_SVM"

    print(f"  --> {subject} Shoeb Replication:")
    print(f"      Sensitivity: {summary['sensitivity']*100:.1f}% ({summary['detected_seizures']}/{summary['total_seizures']})")
    print(f"      False Alarms/hr: {summary['fa_per_hour']:.3f} ({summary['false_alarms']} FA in {summary['non_seizure_hours']:.1f}h)")
    print(f"      Mean Latency: {summary['mean_latency_sec']:.2f} s, Median: {summary['median_latency_sec']:.2f} s")

    return fold_results, summary


def generate_replication_comparison_table(shoeb_metrics: list):
    """
    Generates comparison table between:
    1. Shoeb & Guttag (2010) published numbers
    2. Our Shoeb-style replication on our subjects
    3. Our proposed DWT + Linear SVM on the same subjects
    """
    baseline_csv = RESULTS_DIR / "baseline_metrics.csv"
    if not baseline_csv.exists():
        print("Note: baseline_metrics.csv not found yet. Run train.py first.")
        dwt_df = pd.DataFrame()
    else:
        dwt_df = pd.read_csv(baseline_csv)

    shoeb_df = pd.DataFrame(shoeb_metrics)
    shoeb_df.to_csv(RESULTS_DIR / "shoeb_replication.csv", index=False)

    print("\n" + "="*80)
    print("REPLICATION COMPARISON TABLE (Shoeb & Guttag vs Proposed DWT-Linear SVM)")
    print("="*80)
    print(f"{'Method / Metric':<35} | {'Sensitivity':<15} | {'False Alarms/hr':<18} | {'Median Latency':<15}")
    print("-" * 90)
    print(f"{'Shoeb & Guttag (Published 2010)':<35} | {'96.0% (166/173)':<15} | {'~0.083 (2/24h)':<18} | {'3.0 s':<15}")
    
    if not shoeb_df.empty:
        shoeb_tot_sz = shoeb_df["total_seizures"].sum()
        shoeb_tot_det = shoeb_df["detected_seizures"].sum()
        shoeb_sens = (shoeb_tot_det / shoeb_tot_sz * 100) if shoeb_tot_sz > 0 else 0
        shoeb_fa_hr = (shoeb_df["false_alarms"].sum() / shoeb_df["non_seizure_hours"].sum()) if shoeb_df["non_seizure_hours"].sum() > 0 else 0
        all_lats = []
        for l in shoeb_df["latencies"]:
            all_lats.extend(eval(str(l)))
        shoeb_med_lat = np.median(all_lats) if all_lats else 0.0
        print(f"{'Shoeb Replication (Our Subset)':<35} | {shoeb_sens:.1f}% ({shoeb_tot_det}/{shoeb_tot_sz}){'':<5} | {shoeb_fa_hr:<18.3f} | {shoeb_med_lat:<15.1f}")

    if not dwt_df.empty:
        dwt_tot_sz = dwt_df["total_seizures"].sum()
        dwt_tot_det = dwt_df["detected_seizures"].sum()
        dwt_sens = (dwt_tot_det / dwt_tot_sz * 100) if dwt_tot_sz > 0 else 0
        dwt_fa_hr = (dwt_df["false_alarms"].sum() / dwt_df["non_seizure_hours"].sum()) if dwt_df["non_seizure_hours"].sum() > 0 else 0
        dwt_lats = []
        for l in dwt_df["latencies"]:
            dwt_lats.extend(eval(str(l)))
        dwt_med_lat = np.median(dwt_lats) if dwt_lats else 0.0
        print(f"{'Proposed DWT + Linear SVM':<35} | {dwt_sens:.1f}% ({dwt_tot_det}/{dwt_tot_sz}){'':<5} | {dwt_fa_hr:<18.3f} | {dwt_med_lat:<15.1f}")
    print("="*80)


def main():
    all_summary = []
    for sub in SUBJECTS:
        _, summary = run_shoeb_replication_for_subject(sub)
        if summary:
            all_summary.append(summary)

    if all_summary:
        generate_replication_comparison_table(all_summary)

if __name__ == "__main__":
    main()
