"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Leave-One-Record-Out (LORO) patient-specific training for Linear SVM baseline with db4 wavelet features.
AI-assisted: yes
"""

import sys
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    SUBJECTS,
    PROCESSED_DATA_DIR,
    RESULTS_DIR,
    RANDOM_SEED,
    SVM_C,
    SVM_CLASS_WEIGHT,
    SVM_MAX_ITER,
    WINDOW_SAMPLES,
    BASELINE_BANDS,
    K_CONSECUTIVE
)
from src.dwt import create_causal_bandpass_filter, apply_causal_bandpass
from src.features import extract_record_features
from src.postprocess import apply_k_consecutive_alarm
from src.evaluate import score_record_events, aggregate_subject_metrics

def load_record_data(npz_path: Path):
    """Loads processed .npz record archive."""
    data = np.load(npz_path, allow_pickle=True)
    return {
        "signals": data["signals"],
        "window_starts": data["window_starts"],
        "window_labels": data["window_labels"],
        "seizure_intervals": data["seizure_intervals"],
        "duration_sec": float(data["duration_sec"]),
        "subject": str(data["subject"]),
        "filename": str(data["filename"])
    }


def run_loro_training_for_subject(
    subject: str,
    bands: list = BASELINE_BANDS,
    feature_set: str = "all",
    k: int = K_CONSECUTIVE,
    c_val: float = SVM_C
):
    """
    Executes Leave-One-Record-Out (LORO) cross-validation for a single subject:
    - Standardizes using training records only.
    - Trains LinearSVC with class_weight='balanced'.
    - Runs k-consecutive alarm post-processing.
    - Computes event metrics per held-out record.
    """
    record_files = sorted(list(PROCESSED_DATA_DIR.glob(f"{subject}_*.npz")))
    if len(record_files) < 2:
        print(f"Warning: Only {len(record_files)} records available for {subject}. Need at least 2 for LORO.")
        return [], {}

    print(f"\n--- Running LORO Evaluation for {subject} ({len(record_files)} records) ---")

    # Step 1: Pre-extract features for all records
    sos = create_causal_bandpass_filter()
    records_cache = []

    for fpath in record_files:
        rec = load_record_data(fpath)
        # Apply causal band-pass (state reset per file)
        filtered_sig = apply_causal_bandpass(rec["signals"], sos)
        # Extract features per window
        feats = extract_record_features(
            filtered_sig,
            rec["window_starts"],
            WINDOW_SAMPLES,
            bands=bands,
            feature_set=feature_set
        )
        records_cache.append({
            "filename": rec["filename"],
            "features": feats,
            "window_starts": rec["window_starts"],
            "window_labels": rec["window_labels"],
            "seizure_intervals": rec["seizure_intervals"],
            "duration_sec": rec["duration_sec"]
        })

    # Step 2: LORO Loop
    fold_results = []
    subject_event_scores = []
    models_dir = RESULTS_DIR / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    for test_idx, test_rec in enumerate(records_cache):
        test_fname = test_rec["filename"]
        
        # Assemble training data from all OTHER records of this patient
        train_x_list = []
        train_y_list = []
        for train_idx, tr_rec in enumerate(records_cache):
            if train_idx != test_idx:
                train_x_list.append(tr_rec["features"])
                train_y_list.append(tr_rec["window_labels"])

        X_train = np.vstack(train_x_list)
        y_train = np.concatenate(train_y_list)
        X_test = test_rec["features"]
        y_test = test_rec["window_labels"]

        # Handle degenerate case of no positive windows in training fold
        if np.sum(y_train) == 0:
            print(f"  [Fold {test_fname}] Skipping: No positive training windows in other files.")
            continue

        # Fit scaler on training set ONLY (zero leakage)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train Linear SVM
        clf = LinearSVC(
            C=c_val,
            class_weight=SVM_CLASS_WEIGHT,
            max_iter=SVM_MAX_ITER,
            random_state=RANDOM_SEED,
            dual="auto"
        )
        clf.fit(X_train_scaled, y_train)

        # Predict on held-out test record
        y_pred = clf.predict(X_test_scaled)
        dec_scores = clf.decision_function(X_test_scaled)

        # Post-processing: k consecutive positive windows
        raw_alarms = apply_k_consecutive_alarm(
            y_pred,
            test_rec["window_starts"],
            k=k
        )

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
            "total_windows": len(y_test),
            "pos_windows": int(np.sum(y_test)),
            "num_seizures": event_score["num_seizures"],
            "detected_seizures": event_score["detected_seizures"],
            "false_alarms": event_score["false_alarms"],
            "non_seizure_hours": event_score["non_seizure_hours"],
            "latencies": str(event_score["latencies"])
        })

        # Save model for fold 0 to use in S7 fixed-point model
        if test_idx == 0:
            with open(models_dir / f"{subject}_fold0_model.pkl", "wb") as mf:
                pickle.dump({"clf": clf, "scaler": scaler}, mf)

    # Subject-level summary
    summary_metrics = aggregate_subject_metrics(subject_event_scores)
    summary_metrics["subject"] = subject
    summary_metrics["k"] = k
    summary_metrics["feature_set"] = feature_set
    summary_metrics["num_folds"] = len(fold_results)

    print(f"  --> {subject} LORO Results (k={k}):")
    print(f"      Sensitivity: {summary_metrics['sensitivity']*100:.1f}% ({summary_metrics['detected_seizures']}/{summary_metrics['total_seizures']})")
    print(f"      False Alarms/hr: {summary_metrics['fa_per_hour']:.3f} ({summary_metrics['false_alarms']} FA in {summary_metrics['non_seizure_hours']:.1f}h)")
    print(f"      Mean Latency: {summary_metrics['mean_latency_sec']:.2f} s, Median: {summary_metrics['median_latency_sec']:.2f} s")

    return fold_results, summary_metrics


def main():
    all_fold_rows = []
    all_summary_rows = []

    for sub in SUBJECTS:
        f_rows, s_metric = run_loro_training_for_subject(sub)
        all_fold_rows.extend(f_rows)
        if s_metric:
            all_summary_rows.append(s_metric)

    if all_fold_rows:
        df_folds = pd.DataFrame(all_fold_rows)
        df_folds.to_csv(RESULTS_DIR / "baseline_folds.csv", index=False)

    if all_summary_rows:
        df_summary = pd.DataFrame(all_summary_rows)
        df_summary.to_csv(RESULTS_DIR / "baseline_metrics.csv", index=False)
        print(f"\nSaved baseline evaluation results to {RESULTS_DIR / 'baseline_metrics.csv'}")

if __name__ == "__main__":
    main()
