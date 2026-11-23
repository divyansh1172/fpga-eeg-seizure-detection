"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.evaluation
Purpose: Post-processing alarm logic (k-consecutive persistence, 30s refractory blanking),
         event-level scoring against clinical ground-truth, and result compilation.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
try:
    from .metrics import compute_window_metrics, aggregate_event_metrics
except ImportError:
    from metrics import compute_window_metrics, aggregate_event_metrics

def apply_k_consecutive_alarm(
    window_preds: np.ndarray,
    window_starts_sec: np.ndarray,
    k: int = 3,
    window_sec: float = 1.0
) -> List[float]:
    """
    Asserts a raw alarm after k consecutive positive window predictions.
    The alarm timestamp is defined as the end of the k-th consecutive positive window:
        t_alarm = window_start_sec + window_sec
    """
    alarms: List[float] = []
    consecutive_count = 0
    
    for pred, w_start in zip(window_preds, window_starts_sec):
        if pred == 1:
            consecutive_count += 1
            if consecutive_count >= k:
                # Alarm asserts at the trailing edge of the window
                alarm_time = float(w_start + window_sec)
                alarms.append(alarm_time)
        else:
            consecutive_count = 0
            
    return alarms

def merge_refractory_alarms(alarms: List[float], refractory_sec: float = 30.0) -> List[float]:
    """
    Suppresses alarms that occur within refractory_sec of an active alarm.
    Matches the hardware refractory state machine in rtl/alarm_logic.v.
    """
    if not alarms:
        return []
        
    sorted_alarms = sorted(alarms)
    merged = [sorted_alarms[0]]
    
    for a in sorted_alarms[1:]:
        if a - merged[-1] >= refractory_sec:
            merged.append(a)
            
    return merged

def score_record_events(
    alarms: List[float],
    seizure_intervals: List[Tuple[float, float]],
    duration_sec: float,
    tol_sec: float = 2.0,
    refractory_sec: float = 30.0
) -> Dict[str, Any]:
    """
    Scores detected alarms against ground-truth clinical seizure annotations:
    - Merges raw alarms using refractory_sec.
    - An annotated seizure [onset, offset] is DETECTED if at least one alarm
      falls in the valid detection interval: [onset - tol_sec, offset].
    - Latency is computed as (first matching alarm - onset).
    - Alarms falling outside all valid seizure intervals count as False Alarms.
    - Multiple alarms within the same seizure are not penalized as false alarms.
    """
    merged_alarms = merge_refractory_alarms(alarms, refractory_sec=refractory_sec)
    
    num_seizures = len(seizure_intervals)
    detected_mask = [False] * num_seizures
    latencies: List[float] = []
    alarm_matched = [False] * len(merged_alarms)
    
    for sz_idx, (onset, offset) in enumerate(seizure_intervals):
        valid_start = onset - tol_sec
        valid_end = offset
        
        for a_idx, a_time in enumerate(merged_alarms):
            if valid_start <= a_time <= valid_end:
                if not detected_mask[sz_idx]:
                    detected_mask[sz_idx] = True
                    lat = float(a_time - onset)
                    latencies.append(lat)
                alarm_matched[a_idx] = True
                
    false_alarms = sum(1 for m in alarm_matched if not m)
    
    total_sz_time = sum(max(0.0, offset - onset) for onset, offset in seizure_intervals)
    non_seizure_hours = max(0.0, duration_sec - total_sz_time) / 3600.0
    
    return {
        "num_seizures": num_seizures,
        "detected_seizures": sum(detected_mask),
        "false_alarms": false_alarms,
        "non_seizure_hours": non_seizure_hours,
        "latencies": latencies,
        "merged_alarms": merged_alarms
    }

def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_scores: np.ndarray,
    window_starts_sec: np.ndarray,
    seizure_intervals: List[Tuple[float, float]],
    duration_sec: float,
    k_persistence: int = 3,
    refractory_sec: float = 30.0,
    tolerance_sec: float = 2.0,
    window_sec: float = 1.0
) -> Dict[str, Any]:
    """
    Combined window-level and event-level evaluation on a single recording.
    """
    w_metrics = compute_window_metrics(y_true, y_pred, y_scores)
    
    raw_alarms = apply_k_consecutive_alarm(
        y_pred,
        window_starts_sec,
        k=k_persistence,
        window_sec=window_sec
    )
    
    ev_score = score_record_events(
        raw_alarms,
        seizure_intervals,
        duration_sec=duration_sec,
        tol_sec=tolerance_sec,
        refractory_sec=refractory_sec
    )
    
    return {
        "window_metrics": w_metrics,
        "event_metrics": ev_score
    }
