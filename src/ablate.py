"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Systematic ablation experiments:
         1. k consecutive window sweep in {1, 2, 3, 5}
         2. Feature set ablation: {E, LL, E+LL, log(E)}
         3. Wavelet sub-band ablation: with vs without D2
         4. Regularization parameter C in {0.01, 0.1, 1.0, 10.0}
         Outputs results/ablation_table.csv and results/k_tradeoff.png.
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    SUBJECTS,
    BASELINE_BANDS,
    RESULTS_DIR
)
from src.train import run_loro_training_for_subject

def run_k_ablation():
    """Sweeps k in {1, 2, 3, 5} for alarm post-processing."""
    k_values = [1, 2, 3, 5]
    records = []

    print("\n" + "="*60)
    print("ABLATION 1: Alarm Threshold k in {1, 2, 3, 5}")
    print("="*60)

    for k in k_values:
        k_metrics = []
        for sub in SUBJECTS:
            _, summary = run_loro_training_for_subject(sub, k=k)
            if summary:
                k_metrics.append(summary)

        if k_metrics:
            df = pd.DataFrame(k_metrics)
            tot_sz = df["total_seizures"].sum()
            tot_det = df["detected_seizures"].sum()
            tot_fa = df["false_alarms"].sum()
            tot_hr = df["non_seizure_hours"].sum()

            all_lats = []
            for l in df["latencies"]:
                all_lats.extend(l if isinstance(l, list) else eval(str(l)))

            sens = (tot_det / tot_sz) if tot_sz > 0 else 0
            fa_hr = (tot_fa / tot_hr) if tot_hr > 0 else 0
            med_lat = np.median(all_lats) if all_lats else 0

            records.append({
                "ablation_type": "k_sweep",
                "param_name": "k",
                "param_value": k,
                "sensitivity": sens,
                "fa_per_hour": fa_hr,
                "median_latency_sec": med_lat
            })

    # Plot trade-off curve
    if records:
        df_k = pd.DataFrame(records)
        plt.figure(figsize=(8, 5))
        plt.plot(df_k["fa_per_hour"], df_k["sensitivity"] * 100, marker="o", lw=2, color="#d62728")
        for _, row in df_k.iterrows():
            plt.annotate(
                f"k={int(row['param_value'])}",
                (row["fa_per_hour"], row["sensitivity"] * 100),
                textcoords="offset points",
                xytext=(10, 5),
                fontweight="bold"
            )
        plt.title("Sensitivity vs False Alarms/hr Trade-off across Alarm Parameter k", fontsize=12, fontweight="bold")
        plt.xlabel("False Detections per Hour (FA/h)", fontsize=11)
        plt.ylabel("Event Sensitivity (%)", fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        out_plot = RESULTS_DIR / "k_tradeoff.png"
        plt.savefig(out_plot, dpi=200)
        plt.close()
        print(f"[PLOT] Saved k-trade-off curve to {out_plot}")

    return records


def run_feature_ablation():
    """Sweeps feature sets: Energy only, Line-length only, E+LL, log-energy."""
    feature_sets = ["energy", "linelength", "all", "log_energy"]
    records = []

    print("\n" + "="*60)
    print("ABLATION 2: Feature Sets {E, LL, E+LL, log(E)}")
    print("="*60)

    for f_set in feature_sets:
        f_metrics = []
        for sub in SUBJECTS:
            _, summary = run_loro_training_for_subject(sub, feature_set=f_set, k=3)
            if summary:
                f_metrics.append(summary)

        if f_metrics:
            df = pd.DataFrame(f_metrics)
            tot_sz = df["total_seizures"].sum()
            tot_det = df["detected_seizures"].sum()
            tot_fa = df["false_alarms"].sum()
            tot_hr = df["non_seizure_hours"].sum()
            all_lats = []
            for l in df["latencies"]:
                all_lats.extend(l if isinstance(l, list) else eval(str(l)))

            records.append({
                "ablation_type": "feature_set",
                "param_name": "feature_set",
                "param_value": f_set,
                "sensitivity": (tot_det / tot_sz) if tot_sz > 0 else 0,
                "fa_per_hour": (tot_fa / tot_hr) if tot_hr > 0 else 0,
                "median_latency_sec": np.median(all_lats) if all_lats else 0
            })
    return records


def run_subband_ablation():
    """Ablation on including D2 (32-64 Hz) vs baseline (D3, D4, D5, A5)."""
    configs = [
        ("baseline_no_D2", ["D3", "D4", "D5", "A5"]),
        ("with_D2", ["D2", "D3", "D4", "D5", "A5"])
    ]
    records = []

    print("\n" + "="*60)
    print("ABLATION 3: Sub-band Selection (with vs without D2)")
    print("="*60)

    for name, bands in configs:
        b_metrics = []
        for sub in SUBJECTS:
            _, summary = run_loro_training_for_subject(sub, bands=bands, k=3)
            if summary:
                b_metrics.append(summary)

        if b_metrics:
            df = pd.DataFrame(b_metrics)
            tot_sz = df["total_seizures"].sum()
            tot_det = df["detected_seizures"].sum()
            tot_fa = df["false_alarms"].sum()
            tot_hr = df["non_seizure_hours"].sum()
            all_lats = []
            for l in df["latencies"]:
                all_lats.extend(l if isinstance(l, list) else eval(str(l)))

            records.append({
                "ablation_type": "subbands",
                "param_name": "bands",
                "param_value": name,
                "sensitivity": (tot_det / tot_sz) if tot_sz > 0 else 0,
                "fa_per_hour": (tot_fa / tot_hr) if tot_hr > 0 else 0,
                "median_latency_sec": np.median(all_lats) if all_lats else 0
            })
    return records


def run_c_ablation():
    """Sweeps SVM regularization parameter C in {0.01, 0.1, 1.0, 10.0}."""
    c_values = [0.01, 0.1, 1.0, 10.0]
    records = []

    print("\n" + "="*60)
    print("ABLATION 4: SVM Regularization C in {0.01, 0.1, 1.0, 10.0}")
    print("="*60)

    for c_val in c_values:
        c_metrics = []
        for sub in SUBJECTS:
            _, summary = run_loro_training_for_subject(sub, c_val=c_val, k=3)
            if summary:
                c_metrics.append(summary)

        if c_metrics:
            df = pd.DataFrame(c_metrics)
            tot_sz = df["total_seizures"].sum()
            tot_det = df["detected_seizures"].sum()
            tot_fa = df["false_alarms"].sum()
            tot_hr = df["non_seizure_hours"].sum()
            all_lats = []
            for l in df["latencies"]:
                all_lats.extend(l if isinstance(l, list) else eval(str(l)))

            records.append({
                "ablation_type": "svm_c",
                "param_name": "C",
                "param_value": c_val,
                "sensitivity": (tot_det / tot_sz) if tot_sz > 0 else 0,
                "fa_per_hour": (tot_fa / tot_hr) if tot_hr > 0 else 0,
                "median_latency_sec": np.median(all_lats) if all_lats else 0
            })
    return records


def main():
    all_ablations = []
    all_ablations.extend(run_k_ablation())
    all_ablations.extend(run_feature_ablation())
    all_ablations.extend(run_subband_ablation())
    all_ablations.extend(run_c_ablation())

    if all_ablations:
        df_all = pd.DataFrame(all_ablations)
        out_csv = RESULTS_DIR / "ablation_table.csv"
        df_all.to_csv(out_csv, index=False)
        print(f"\n[DONE] Saved complete ablation table to {out_csv}")

if __name__ == "__main__":
    main()
