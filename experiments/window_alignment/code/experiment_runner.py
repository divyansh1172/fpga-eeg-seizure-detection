"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.experiment_runner
Purpose: Central experiment orchestrator for patient-specific Leave-One-Record-Out (LORO)
         cross-validation, model training, standardization, and evaluation under
         explicit window configurations (Configuration A: 1.0s vs Configuration B: 2.0s).
"""

import os
import sys
import argparse
import json
import pickle
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Add project root to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
EXP_DIR = SCRIPT_DIR.parent
PROJ_ROOT = EXP_DIR.parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

try:
    from .config_loader import load_config
    from .metrics import compute_window_metrics, aggregate_event_metrics
    from .evaluation import evaluate_predictions
    from .feature_pipeline import (
        create_causal_bandpass_filter,
        apply_causal_bandpass,
        extract_window_features_176,
        generate_window_slices
    )
except ImportError:
    from config_loader import load_config
    from metrics import compute_window_metrics, aggregate_event_metrics
    from evaluation import evaluate_predictions
    from feature_pipeline import (
        create_causal_bandpass_filter,
        apply_causal_bandpass,
        extract_window_features_176,
        generate_window_slices
    )

# Standard Scaler implementation with zero external dependency requirement
class SimpleStandardScaler:
    """
    StandardScaler implementation matching scikit-learn behavior:
    z = (x - mean) / std.
    """
    def __init__(self):
        self.mean_ = None
        self.scale_ = None
        self.n_samples_seen_ = 0

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=np.float64)
        self.mean_ = np.mean(X, axis=0)
        var = np.var(X, axis=0)
        # Avoid division by zero
        self.scale_ = np.sqrt(np.where(var == 0, 1.0, var))
        self.n_samples_seen_ = X.shape[0]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return (X - self.mean_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

def _get_linear_classifier(C: float = 1.0, class_weight: str = "balanced", random_seed: int = 42, max_iter: int = 20000):
    """
    Returns LinearSVC classifier from scikit-learn if available,
    or a fallback pure-NumPy Pegasos/SGD linear SVM solver.
    """
    try:
        from sklearn.svm import LinearSVC
        return LinearSVC(
            C=C,
            class_weight=class_weight,
            random_state=random_seed,
            max_iter=max_iter,
            dual="auto"
        )
    except ImportError:
        # Fallback pure-NumPy Linear SVM solver using Subgradient Descent (Pegasos)
        class NumpyLinearSVM:
            def __init__(self, C=1.0, max_iter=20000, random_state=42):
                self.C = C
                self.max_iter = max_iter
                self.random_state = random_state
                self.coef_ = None
                self.intercept_ = None

            def fit(self, X, y):
                np.random.seed(self.random_state)
                X = np.asarray(X, dtype=np.float64)
                # Map labels to {-1, +1}
                y_bin = np.where(np.asarray(y) == 1, 1.0, -1.0)
                n_samples, n_features = X.shape
                
                # Class weights
                n_pos = np.sum(y_bin == 1.0)
                n_neg = np.sum(y_bin == -1.0)
                w_pos = n_samples / (2.0 * max(1, n_pos))
                w_neg = n_samples / (2.0 * max(1, n_neg))
                sample_weights = np.where(y_bin == 1.0, w_pos, w_neg)
                
                # Subgradient descent
                w = np.zeros(n_features, dtype=np.float64)
                b = 0.0
                lambda_param = 1.0 / (self.C * n_samples)
                
                lr0 = 0.01
                for it in range(1, min(self.max_iter, 5000) + 1):
                    lr = lr0 / np.sqrt(it)
                    idx = np.random.randint(0, n_samples)
                    xi = X[idx]
                    yi = y_bin[idx]
                    swi = sample_weights[idx]
                    
                    margin = yi * (np.dot(w, xi) + b)
                    if margin < 1.0:
                        w = (1.0 - lr * lambda_param) * w + lr * self.C * swi * yi * xi
                        b = b + lr * self.C * swi * yi * 0.1
                    else:
                        w = (1.0 - lr * lambda_param) * w
                        
                self.coef_ = np.array([w], dtype=np.float64)
                self.intercept_ = np.array([b], dtype=np.float64)
                return self

            def decision_function(self, X):
                X = np.asarray(X, dtype=np.float64)
                return np.dot(X, self.coef_[0]) + self.intercept_[0]

            def predict(self, X):
                scores = self.decision_function(X)
                return np.where(scores > 0.0, 1, 0)

        return NumpyLinearSVM(C=C, max_iter=max_iter, random_state=random_seed)

class ExperimentRunner:
    """
    Manages end-to-end dataset feature preparation, LORO cross-validation,
    model artifact persistence, and report generation.
    """
    def __init__(self, config_path_or_name: str, base_dir: Optional[Path] = None):
        self.config = load_config(config_path_or_name)
        self.base_dir = base_dir or PROJ_ROOT
        self.exp_name = self.config["name"]
        
        # Directories
        self.data_dir = self.base_dir / "data"
        self.raw_data_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.results_dir = EXP_DIR / "reports" / self.exp_name
        self.models_dir = EXP_DIR / "artifacts" / self.exp_name / "models"
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def extract_features_from_signals(
        self,
        signals: np.ndarray,
        window_starts_sample: np.ndarray,
        window_samples: int
    ) -> np.ndarray:
        """
        Extracts 176 features for each window slice in a recording.
        signals shape: (22, total_samples)
        """
        num_windows = len(window_starts_sample)
        if num_windows == 0:
            return np.empty((0, 176), dtype=np.float32)
            
        features = np.zeros((num_windows, 176), dtype=np.float32)
        retained_bands = self.config["wavelet"]["retained_subbands"]
        
        for w_i, s_start in enumerate(window_starts_sample):
            w_sig = signals[:, s_start : s_start + window_samples]
            features[w_i, :] = extract_window_features_176(w_sig, retained_bands=retained_bands)
            
        return features

    def load_or_process_subject_records(self, subject: str) -> List[Dict[str, Any]]:
        """
        Loads preprocessed .npz records for a subject, or generates them dynamically.
        Returns list of record dictionaries with features, window timestamps, and labels.
        """
        # Check if preprocessed .npz files exist in data/processed
        npz_files = sorted(list(self.processed_dir.glob(f"{subject}_*.npz")))
        
        window_samples = self.config["windowing"]["window_samples"]
        hop_samples = self.config["windowing"]["hop_samples"]
        fs = self.config["sampling"]["frequency_hz"]
        label_thresh = self.config["windowing"]["label_overlap_threshold"]
        
        sos = create_causal_bandpass_filter(
            fs=fs,
            low_hz=self.config["preprocessing"]["bandpass_low_hz"],
            high_hz=self.config["preprocessing"]["bandpass_high_hz"],
            order=self.config["preprocessing"]["iir_order"]
        )
        
        records = []
        for npz_path in npz_files:
            data = np.load(npz_path, allow_pickle=True)
            raw_sig = data["signals"]
            num_samples = raw_sig.shape[1]
            sz_intervals = [tuple(x) for x in data["seizure_intervals"]]
            
            # Apply causal bandpass
            filt_sig = apply_causal_bandpass(raw_sig, sos)
            
            # Generate window slices for THIS experiment configuration
            starts_samp, starts_sec, labels = generate_window_slices(
                num_samples=num_samples,
                window_samples=window_samples,
                hop_samples=hop_samples,
                fs=fs,
                seizure_intervals=sz_intervals,
                label_overlap_thresh=label_thresh
            )
            
            # Extract 176 features
            feats = self.extract_features_from_signals(filt_sig, starts_samp, window_samples)
            
            records.append({
                "subject": str(data.get("subject", subject)),
                "filename": str(data.get("filename", npz_path.stem)),
                "features": feats,
                "window_starts_sec": starts_sec,
                "window_labels": labels,
                "seizure_intervals": sz_intervals,
                "duration_sec": float(data.get("duration_sec", num_samples / fs)),
                "total_windows": len(labels),
                "positive_windows": int(np.sum(labels))
            })
            
        return records

    def run_loro_for_subject(self, subject: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Executes strict Leave-One-Record-Out (LORO) cross-validation for a single subject:
        - Trains on (M - 1) records.
        - Scales using train fold ONLY.
        - Evaluates on the held-out record.
        - Repeats for all M records.
        """
        records = self.load_or_process_subject_records(subject)
        if len(records) < 2:
            print(f"[WARN] Insufficient records ({len(records)}) for LORO cross-validation on {subject}.")
            return [], {}
            
        print(f"\n================================================================================")
        print(f" LORO Evaluation: {subject} ({len(records)} records) | Config: {self.exp_name}")
        print(f"================================================================================")
        
        fold_results = []
        event_scores = []
        
        cfg_clf = self.config["classifier"]
        cfg_post = self.config["postprocess"]
        w_sec = self.config["windowing"]["window_sec"]
        
        for test_idx, test_rec in enumerate(records):
            test_fname = test_rec["filename"]
            
            # Assemble training data from all OTHER records of this patient
            train_feats_list = []
            train_labels_list = []
            
            for tr_idx, tr_rec in enumerate(records):
                if tr_idx != test_idx:
                    train_feats_list.append(tr_rec["features"])
                    train_labels_list.append(tr_rec["window_labels"])
                    
            X_train = np.vstack(train_feats_list)
            y_train = np.concatenate(train_labels_list)
            X_test = test_rec["features"]
            y_test = test_rec["window_labels"]
            
            # Skip degenerate fold with zero positive training samples
            if np.sum(y_train) == 0:
                print(f"  [Fold {test_fname}] Skipping: No seizure windows in training portion.")
                continue
                
            # Fit scaler on TRAINING SET ONLY (zero-leakage invariant)
            scaler = SimpleStandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Linear SVM
            clf = _get_linear_classifier(
                C=cfg_clf["C"],
                class_weight=cfg_clf["class_weight"],
                random_seed=cfg_clf["random_seed"],
                max_iter=cfg_clf["max_iter"]
            )
            clf.fit(X_train_scaled, y_train)
            
            # Predict and score on held-out test record
            y_pred = clf.predict(X_test_scaled)
            scores = clf.decision_function(X_test_scaled)
            
            eval_out = evaluate_predictions(
                y_true=y_test,
                y_pred=y_pred,
                y_scores=scores,
                window_starts_sec=test_rec["window_starts_sec"],
                seizure_intervals=test_rec["seizure_intervals"],
                duration_sec=test_rec["duration_sec"],
                k_persistence=cfg_post["k_persistence"],
                refractory_sec=cfg_post["refractory_sec"],
                tolerance_sec=cfg_post["tolerance_sec"],
                window_sec=w_sec
            )
            
            w_m = eval_out["window_metrics"]
            ev_m = eval_out["event_metrics"]
            event_scores.append(ev_m)
            
            fold_row = {
                "subject": subject,
                "held_out_record": test_fname,
                "total_windows": w_m["total_windows"],
                "pos_windows": w_m["positive_windows"],
                "window_sensitivity": round(w_m["sensitivity"], 4),
                "window_specificity": round(w_m["specificity"], 4),
                "window_f1": round(w_m["f1_score"], 4),
                "roc_auc": round(w_m["roc_auc"], 4) if not np.isnan(w_m["roc_auc"]) else None,
                "num_seizures": ev_m["num_seizures"],
                "detected_seizures": ev_m["detected_seizures"],
                "false_alarms": ev_m["false_alarms"],
                "non_seizure_hours": round(ev_m["non_seizure_hours"], 3),
                "latencies": str(ev_m["latencies"])
            }
            fold_results.append(fold_row)
            
            # Persist fold model
            fold_model_path = self.models_dir / f"{subject}_{Path(test_fname).stem}_model.pkl"
            with open(fold_model_path, "wb") as mf:
                pickle.dump({"clf": clf, "scaler": scaler, "config": self.config}, mf)
                
            print(f"  [Fold {test_fname[:16]:16s}] Seizures: {ev_m['detected_seizures']}/{ev_m['num_seizures']} | "
                  f"FA: {ev_m['false_alarms']} | Windows: {w_m['total_windows']}")
                  
        # Train a deployment model on ALL eligible records for this patient
        self._train_and_save_deployment_model(subject, records)
        
        # Summary
        subject_summary = aggregate_event_metrics(event_scores)
        subject_summary["subject"] = subject
        subject_summary["config_name"] = self.exp_name
        subject_summary["window_sec"] = w_sec
        subject_summary["k_persistence"] = cfg_post["k_persistence"]
        subject_summary["num_folds"] = len(fold_results)
        
        print(f"\n  ---> {subject} LORO Summary:")
        print(f"       Sensitivity: {subject_summary['seizure_sensitivity']*100:.1f}% ({subject_summary['detected_seizures']}/{subject_summary['total_seizures']})")
        print(f"       False Alarms/hr: {subject_summary['false_alarms_per_hour']:.3f} ({subject_summary['total_false_alarms']} FA in {subject_summary['non_seizure_hours']:.1f}h)")
        print(f"       Latency: median={subject_summary['median_latency_sec']}s, mean={subject_summary['mean_latency_sec']}s")
        
        return fold_results, subject_summary

    def _train_and_save_deployment_model(self, subject: str, records: List[Dict[str, Any]]):
        """
        Trains a final candidate deployment model using ALL eligible records of the subject.
        IMPORTANT: Clearly marked as a deployment candidate. It is NOT presented as having
        an independent evaluation result.
        """
        all_x = np.vstack([r["features"] for r in records])
        all_y = np.concatenate([r["window_labels"] for r in records])
        
        if np.sum(all_y) == 0:
            return
            
        scaler = SimpleStandardScaler()
        X_scaled = scaler.fit_transform(all_x)
        
        cfg_clf = self.config["classifier"]
        clf = _get_linear_classifier(
            C=cfg_clf["C"],
            class_weight=cfg_clf["class_weight"],
            random_seed=cfg_clf["random_seed"],
            max_iter=cfg_clf["max_iter"]
        )
        clf.fit(X_scaled, all_y)
        
        deploy_path = self.models_dir / f"{subject}_deployment_candidate.pkl"
        with open(deploy_path, "wb") as f:
            pickle.dump({
                "clf": clf,
                "scaler": scaler,
                "config": self.config,
                "is_deployment_candidate": True,
                "trained_on_all_records": True,
                "num_records": len(records),
                "total_windows": len(all_y),
                "positive_windows": int(np.sum(all_y))
            }, f)
        print(f"  [DEPLOY] Saved full-dataset deployment candidate model -> {deploy_path.name}")

    def run_all_subjects(self) -> Dict[str, Any]:
        """
        Executes LORO cross-validation across all subjects specified in config.
        Exports consolidated CSVs and JSON summary reports.
        """
        subjects = self.config["evaluation"]["subjects"]
        all_folds: List[Dict[str, Any]] = []
        all_summaries: List[Dict[str, Any]] = []
        
        start_t = time.time()
        for sub in subjects:
            f_rows, s_summ = self.run_loro_for_subject(sub)
            all_folds.extend(f_rows)
            if s_summ:
                all_summaries.append(s_summ)
                
        elapsed = time.time() - start_t
        
        # Export fold-level results to CSV
        if all_folds:
            csv_path = self.results_dir / "loro_folds.csv"
            _write_dicts_to_csv(all_folds, csv_path)
            print(f"\n[REPORT] Saved fold-level LORO metrics -> {csv_path}")
            
        # Export summary metrics
        if all_summaries:
            summary_csv = self.results_dir / "summary_metrics.csv"
            _write_dicts_to_csv(all_summaries, summary_csv)
            summary_json = self.results_dir / "summary_metrics.json"
            with open(summary_json, "w", encoding="utf-8") as jf:
                json.dump({"config": self.config, "subjects": all_summaries, "elapsed_sec": round(elapsed, 2)}, jf, indent=2)
            print(f"[REPORT] Saved summary metrics -> {summary_csv}")
            
        return {
            "folds": all_folds,
            "summaries": all_summaries,
            "elapsed_sec": elapsed
        }

def _write_dicts_to_csv(rows: List[Dict[str, Any]], out_path: Path):
    """Zero-dependency CSV writer."""
    if not rows:
        return
    import csv
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description="Run EEG Seizure Detector Model Training and LORO Evaluation.")
    parser.add_argument("--config", type=str, default="1s", help="Config name or path ('1s', '2s', or path)")
    parser.add_argument("--subject", type=str, default="all", help="Subject ('chb01', 'chb02', 'chb03', or 'all')")
    args = parser.parse_args()
    
    runner = ExperimentRunner(config_path_or_name=args.config)
    if args.subject.lower() == "all":
        runner.run_all_subjects()
    else:
        runner.run_loro_for_subject(args.subject.lower())

if __name__ == "__main__":
    main()
