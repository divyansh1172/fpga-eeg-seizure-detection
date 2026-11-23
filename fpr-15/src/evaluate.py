"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Event-based scoring logic (Sensitivity, False Alarms/hr, Latency) and synthetic unit tests.
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    EVENT_TOLERANCE_SEC,
    EVENT_REFRACTORY_SEC
)

def merge_refractory_alarms(alarms: list, refractory_sec: float = EVENT_REFRACTORY_SEC) -> list:
    """
    Merges alarms occurring within refractory_sec of each other.
    The first alarm in a cluster is kept; subsequent alarms within refractory_sec are dropped.
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
    alarms: list,
    seizure_intervals: list,
    duration_sec: float,
    tol_sec: float = EVENT_TOLERANCE_SEC,
    refractory_sec: float = EVENT_REFRACTORY_SEC
) -> dict:
    """
    Scores detection events against annotated ground-truth seizures.
    Scoring rules:
    - Alarms within refractory_sec are merged.
    - A seizure [onset, offset] is detected if at least one alarm falls in [onset - tol_sec, offset].
    - Multiple alarms within the same seizure are not penalized as false alarms.
    - Alarms outside all valid seizure detection windows count as false alarms.
    """
    merged_alarms = merge_refractory_alarms(alarms, refractory_sec=refractory_sec)

    num_seizures = len(seizure_intervals)
    detected_mask = [False] * num_seizures
    latencies = []
    alarm_matched = [False] * len(merged_alarms)

    for sz_idx, (onset, offset) in enumerate(seizure_intervals):
        # Valid detection interval
        valid_start = onset - tol_sec
        valid_end = offset

        # Find first matching alarm
        for a_idx, a_time in enumerate(merged_alarms):
            if valid_start <= a_time <= valid_end:
                if not detected_mask[sz_idx]:
                    detected_mask[sz_idx] = True
                    # Latency = first alarm time - onset
                    latencies.append(float(a_time - onset))
                alarm_matched[a_idx] = True

    # Any alarm that did not match a valid seizure interval is a false alarm
    false_alarms = sum(1 for matched in alarm_matched if not matched)

    # Calculate non-seizure recording time (hours)
    total_seizure_time = sum(max(0.0, offset - onset) for onset, offset in seizure_intervals)
    non_seizure_hours = max(0.0, duration_sec - total_seizure_time) / 3600.0

    return {
        "num_seizures": num_seizures,
        "detected_seizures": sum(detected_mask),
        "false_alarms": false_alarms,
        "non_seizure_hours": non_seizure_hours,
        "latencies": latencies
    }


def aggregate_subject_metrics(records_scores: list) -> dict:
    """
    Aggregates per-record scoring dicts for a subject into pooled metrics:
    - Event Sensitivity
    - False Alarms per Hour (FA/h)
    - Mean and Median Latency
    """
    total_sz = sum(r["num_seizures"] for r in records_scores)
    total_det = sum(r["detected_seizures"] for r in records_scores)
    total_fa = sum(r["false_alarms"] for r in records_scores)
    total_hours = sum(r["non_seizure_hours"] for r in records_scores)

    all_latencies = []
    for r in records_scores:
        all_latencies.extend(r["latencies"])

    sensitivity = (total_det / total_sz) if total_sz > 0 else 0.0
    fa_per_hour = (total_fa / total_hours) if total_hours > 0 else 0.0
    mean_lat = float(np.mean(all_latencies)) if all_latencies else 0.0
    median_lat = float(np.median(all_latencies)) if all_latencies else 0.0

    return {
        "total_seizures": total_sz,
        "detected_seizures": total_det,
        "sensitivity": sensitivity,
        "false_alarms": total_fa,
        "non_seizure_hours": total_hours,
        "fa_per_hour": fa_per_hour,
        "mean_latency_sec": mean_lat,
        "median_latency_sec": median_lat,
        "latencies": all_latencies
    }


def run_unit_tests():
    """
    Synthetic unit tests for the event scoring logic:
    1. Single alarm inside seizure -> 1 detected, 0 FA
    2. Early alarm within tolerance (onset - 1s) -> 1 detected, 0 FA
    3. Early alarm outside tolerance (onset - 5s) -> 0 detected, 1 FA
    4. Duplicate alarms in same seizure -> 1 detected, 0 FA (no duplicate penalty)
    5. Pure false alarm in seizure-free period -> 0 detected, 1 FA
    6. Refractory merging of rapid alarms -> merged to single alarm
    """
    print("Running scoring unit tests...")

    seizure = [(100.0, 150.0)]
    dur = 3600.0  # 1 hour

    # Test 1: Alarm inside seizure at 110s
    res1 = score_record_events([110.0], seizure, dur)
    assert res1["detected_seizures"] == 1 and res1["false_alarms"] == 0, f"Test 1 failed: {res1}"
    assert np.isclose(res1["latencies"][0], 10.0), f"Test 1 latency failed: {res1}"

    # Test 2: Early alarm at 99s (tolerance is 2s, onset is 100s) -> valid
    res2 = score_record_events([99.0], seizure, dur)
    assert res2["detected_seizures"] == 1 and res2["false_alarms"] == 0, f"Test 2 failed: {res2}"
    assert np.isclose(res2["latencies"][0], -1.0), f"Test 2 latency failed: {res2}"

    # Test 3: Early alarm at 90s (outside tolerance) -> 0 detected, 1 FA
    res3 = score_record_events([90.0], seizure, dur)
    assert res3["detected_seizures"] == 0 and res3["false_alarms"] == 1, f"Test 3 failed: {res3}"

    # Test 4: Duplicate alarms inside seizure (110s, 120s, 130s)
    res4 = score_record_events([110.0, 120.0, 130.0], seizure, dur)
    assert res4["detected_seizures"] == 1 and res4["false_alarms"] == 0, f"Test 4 failed: {res4}"

    # Test 5: False alarm in seizure-free file
    res5 = score_record_events([500.0], [], dur)
    assert res5["detected_seizures"] == 0 and res5["false_alarms"] == 1, f"Test 5 failed: {res5}"

    # Test 6: Refractory merging (alarms at 500s and 510s) -> merged to 1 alarm
    merged = merge_refractory_alarms([500.0, 510.0, 540.0], refractory_sec=30.0)
    assert len(merged) == 2, f"Refractory merge failed: {merged}"
    assert merged[0] == 500.0 and merged[1] == 540.0

    print("All scoring unit tests passed successfully!")

if __name__ == "__main__":
    run_unit_tests()
