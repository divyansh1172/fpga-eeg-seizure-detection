"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.metrics
Purpose: Comprehensive, mathematically rigorous metrics computation for both
         window-level classification and clinical event-level seizure detection.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

def compute_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, int]:
    """
    Computes binary confusion matrix counts: TP, FP, TN, FN.
    y_true and y_pred must be binary (0 or 1).
    """
    y_true = np.asarray(y_true, dtype=np.int32)
    y_pred = np.asarray(y_pred, dtype=np.int32)
    
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    
    return {"TP": tp, "FP": fp, "TN": tn, "FN": fn}

def compute_roc_auc(y_true: np.ndarray, y_scores: np.ndarray) -> float:
    """
    Computes Area Under the ROC Curve (ROC-AUC) using Mann-Whitney U / trapezoidal integration.
    Does not require external scikit-learn dependency.
    """
    y_true = np.asarray(y_true, dtype=np.int32)
    y_scores = np.asarray(y_scores, dtype=np.float64)
    
    pos_mask = (y_true == 1)
    neg_mask = (y_true == 0)
    n_pos = int(np.sum(pos_mask))
    n_neg = int(np.sum(neg_mask))
    
    if n_pos == 0 or n_neg == 0:
        return float("nan")
        
    # Rank scores
    order = np.argsort(y_scores)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(y_scores) + 1)
    
    # Handle tied scores
    sorted_scores = y_scores[order]
    unique_scores, inverse, counts = np.unique(sorted_scores, return_inverse=True, return_counts=True)
    if len(unique_scores) < len(y_scores):
        tie_ranks = np.zeros(len(unique_scores), dtype=np.float64)
        np.add.at(tie_ranks, inverse, ranks[order])
        tie_ranks /= counts
        ranks = tie_ranks[np.searchsorted(unique_scores, y_scores)]
        
    pos_rank_sum = np.sum(ranks[pos_mask])
    u_stat = pos_rank_sum - (n_pos * (n_pos + 1)) / 2.0
    auc = u_stat / (n_pos * n_neg)
    return float(np.clip(auc, 0.0, 1.0))

def compute_window_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_scores: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """
    Computes all standard window-level binary classification metrics:
    - Sensitivity (Recall)
    - Specificity
    - Precision (PPV)
    - F1-Score
    - Balanced Accuracy
    - ROC-AUC (if y_scores provided)
    """
    cm = compute_confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn = cm["TP"], cm["FP"], cm["TN"], cm["FN"]
    total = tp + fp + tn + fn
    
    sens = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    f1 = float(2 * prec * sens / (prec + sens)) if (prec + sens) > 0 else 0.0
    bal_acc = float((sens + spec) / 2.0)
    
    auc = compute_roc_auc(y_true, y_scores) if y_scores is not None else float("nan")
    
    return {
        "confusion_matrix": cm,
        "total_windows": total,
        "positive_windows": tp + fn,
        "negative_windows": tn + fp,
        "sensitivity": sens,
        "specificity": spec,
        "precision": prec,
        "f1_score": f1,
        "balanced_accuracy": bal_acc,
        "roc_auc": auc
    }

def aggregate_event_metrics(event_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates per-record event scoring dictionaries into pooled clinical metrics:
    - Event Sensitivity = total_detected_seizures / total_seizures
    - False Alarm Rate = total_false_alarms / total_non_seizure_hours
    - Latency distribution (median, mean, std, min, max)
    """
    total_sz = sum(r["num_seizures"] for r in event_records)
    detected_sz = sum(r["detected_seizures"] for r in event_records)
    total_fa = sum(r["false_alarms"] for r in event_records)
    total_hours = sum(r["non_seizure_hours"] for r in event_records)
    
    all_latencies = []
    for r in event_records:
        lats = r.get("latencies", [])
        if isinstance(lats, str):
            import ast
            try:
                lats = ast.literal_eval(lats)
            except Exception:
                lats = []
        all_latencies.extend(lats)
        
    sens = float(detected_sz / total_sz) if total_sz > 0 else 0.0
    fa_per_h = float(total_fa / total_hours) if total_hours > 0 else 0.0
    
    if all_latencies:
        mean_lat = float(np.mean(all_latencies))
        med_lat = float(np.median(all_latencies))
        std_lat = float(np.std(all_latencies))
        min_lat = float(np.min(all_latencies))
        max_lat = float(np.max(all_latencies))
    else:
        mean_lat = float("nan")
        med_lat = float("nan")
        std_lat = float("nan")
        min_lat = float("nan")
        max_lat = float("nan")
        
    return {
        "total_seizures": total_sz,
        "detected_seizures": detected_sz,
        "seizure_sensitivity": sens,
        "total_false_alarms": total_fa,
        "non_seizure_hours": round(total_hours, 3),
        "false_alarms_per_hour": round(fa_per_h, 3),
        "mean_latency_sec": round(mean_lat, 2) if not np.isnan(mean_lat) else None,
        "median_latency_sec": round(med_lat, 2) if not np.isnan(med_lat) else None,
        "std_latency_sec": round(std_lat, 2) if not np.isnan(std_lat) else None,
        "min_latency_sec": round(min_lat, 2) if not np.isnan(min_lat) else None,
        "max_latency_sec": round(max_lat, 2) if not np.isnan(max_lat) else None,
        "all_latencies": all_latencies
    }
