"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Temporal post-processing: k-consecutive positive window alarm logic.
AI-assisted: yes
"""

import sys
from pathlib import Path
import numpy as np

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    K_CONSECUTIVE,
    WINDOW_SEC,
    HOP_SEC,
    FS
)

def apply_k_consecutive_alarm(
    window_preds: np.ndarray,
    window_starts: np.ndarray,
    k: int = K_CONSECUTIVE,
    window_sec: float = WINDOW_SEC,
    fs: int = FS
) -> list:
    """
    Asserts an alarm after k consecutive positive window predictions.
    The alarm timestamp is defined as the end of the k-th consecutive positive window.
    Returns: list of alarm timestamps in seconds.
    """
    alarms = []
    consecutive_count = 0

    for i, pred in enumerate(window_preds):
        if pred == 1:
            consecutive_count += 1
            if consecutive_count == k:
                # Alarm triggered at the end of this k-th window
                w_start_sec = window_starts[i] / fs
                alarm_time = w_start_sec + window_sec
                alarms.append(float(alarm_time))
        else:
            consecutive_count = 0

    return alarms
