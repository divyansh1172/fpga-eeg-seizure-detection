"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Dataset I/O, summary file parsing, subject selection rule evaluation, manifest creation, and EDF reader.
AI-assisted: yes
"""

import os
import sys
import re
import urllib.request
from pathlib import Path
import pandas as pd
import numpy as np
import pyedflib

PROJ_ROOT = Path(__file__).resolve().parent.parent
if str(PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJ_ROOT))

from src.config import (
    BASE_DIR,
    DATA_DIR,
    RAW_DATA_DIR,
    MANIFEST_PATH,
    FS,
    SUBJECTS,
    CHANNELS_22,
    CHANNELS_23_RAW,
    ACTIVE_CHANNELS
)

PHYSIOMET_BASE_URL = "https://physionet.org/files/chbmit/1.0.0/"

def download_summary_file(case_id: str, out_dir: Path) -> Path:
    """Download chbXX-summary.txt if not present."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{case_id}-summary.txt"
    if out_path.exists() and out_path.stat().st_size > 0:
        return out_path
    
    url = f"{PHYSIOMET_BASE_URL}{case_id}/{case_id}-summary.txt"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8", errors="replace")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path


def parse_summary_file(summary_path: Path):
    """
    Parse a chbXX-summary.txt file into channel metadata and file-level records.
    Returns:
        header_text: str
        channels: list of str
        records: list of dicts with keys:
            filename, start_time, end_time, num_seizures, seizures: [(start, end), ...]
    """
    with open(summary_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = text.split("File Name:")
    header = blocks[0]

    # Extract channels from header
    channels = re.findall(r"Channel \d+:\s*(.+)", header)
    channels = [c.strip() for c in channels if c.strip()]

    records = []
    for b in blocks[1:]:
        lines = b.strip().splitlines()
        if not lines:
            continue
        filename = lines[0].strip()
        
        m_start = re.search(r"File Start Time:\s*([0-9:]+)", b)
        m_end = re.search(r"File End Time:\s*([0-9:]+)", b)
        start_time = m_start.group(1) if m_start else ""
        end_time = m_end.group(1) if m_end else ""

        m_num = re.search(r"Number of Seizures in File:\s*(\d+)", b)
        num_seizures = int(m_num.group(1)) if m_num else 0

        seizures = []
        if num_seizures > 0:
            starts = re.findall(r"Seizure (?:\d+ )?Start Time:\s*(\d+)\s*seconds", b, re.IGNORECASE)
            ends = re.findall(r"Seizure (?:\d+ )?End Time:\s*(\d+)\s*seconds", b, re.IGNORECASE)
            for s, e in zip(starts, ends):
                seizures.append((int(s), int(e)))

        records.append({
            "filename": filename,
            "start_time": start_time,
            "end_time": end_time,
            "num_seizures": num_seizures,
            "seizures": seizures
        })

    return header, channels, records


def evaluate_subject_rules(summary_dir: Path):
    """
    Applies the subject rule mechanically across all cases in numeric order:
    1. Case must have >= 3 annotated seizures.
    2. Case must have a consistent 23-channel bipolar montage with no non-EEG signals (e.g. ECG, VNS).
    3. Exclude chb21 because it is from the same subject as chb01.
    """
    results = []
    selected = []

    for i in range(1, 25):
        case_id = f"chb{i:02d}"
        if case_id == "chb21":
            results.append({
                "case": case_id,
                "seizures": 0,
                "channels": 0,
                "status": "FAIL",
                "reason": "Excluded: duplicate subject (same patient as chb01)"
            })
            continue

        try:
            summary_path = download_summary_file(case_id, summary_dir)
            header, channels, records = parse_summary_file(summary_path)
            total_seizures = sum(r["num_seizures"] for r in records)
            
            with open(summary_path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()

            has_ecg = "ECG" in full_text
            has_vns = "VNS" in full_text
            channel_count = len(channels)

            passes_seizures = total_seizures >= 3
            passes_channels = (channel_count == 23) and not (has_ecg or has_vns)

            if passes_seizures and passes_channels:
                status = "PASS"
                reason = "Eligible (>=3 seizures, clean 23-ch montage)"
                if len(selected) < 3:
                    selected.append(case_id)
            else:
                status = "FAIL"
                reasons = []
                if not passes_seizures:
                    reasons.append(f"Insufficient seizures ({total_seizures} < 3)")
                if channel_count != 23:
                    reasons.append(f"Channel count ({channel_count} != 23)")
                if has_ecg or has_vns:
                    reasons.append("Non-EEG channel present (ECG/VNS)")
                reason = "; ".join(reasons)

            results.append({
                "case": case_id,
                "seizures": total_seizures,
                "channels": channel_count,
                "status": status,
                "reason": reason
            })
        except Exception as e:
            results.append({
                "case": case_id,
                "seizures": 0,
                "channels": 0,
                "status": "ERROR",
                "reason": str(e)
            })

    return results, selected


def build_manifest(summary_dir: Path, target_seizure_free_hours: int = 10) -> pd.DataFrame:
    """
    Constructs the frozen data/manifest.csv for the selected subjects.
    For each subject:
    - Includes ALL seizure-containing EDF records.
    - Selects seizure-free EDF records up to target_seizure_free_hours (approx 1h per file).
    """
    rows = []
    for case_id in SUBJECTS:
        summary_path = summary_dir / f"{case_id}-summary.txt"
        if not summary_path.exists():
            summary_path = download_summary_file(case_id, summary_dir)

        _, channels, records = parse_summary_file(summary_path)

        seizure_files = [r for r in records if r["num_seizures"] > 0]
        seizure_free_files = [r for r in records if r["num_seizures"] == 0]

        # Take all seizure files
        for r in seizure_files:
            rows.append({
                "subject": case_id,
                "filename": r["filename"],
                "is_seizure_file": 1,
                "num_seizures": r["num_seizures"],
                "seizure_intervals": str(r["seizures"]),
                "selected": 1,
                "selection_reason": "Seizure-containing file (mandatory for sensitivity & LORO)"
            })

        # Take seizure-free files up to target hours (each file is nominally ~1 hour = 3600s)
        for r in seizure_free_files[:target_seizure_free_hours]:
            rows.append({
                "subject": case_id,
                "filename": r["filename"],
                "is_seizure_file": 0,
                "num_seizures": 0,
                "seizure_intervals": "[]",
                "selected": 1,
                "selection_reason": "Seizure-free background (for false alarm / hour estimation)"
            })

    df = pd.DataFrame(rows)
    df.to_csv(MANIFEST_PATH, index=False)
    return df


def read_edf(edf_path: Path, active_channels=ACTIVE_CHANNELS):
    """
    Reads an EDF file, verifies sampling frequency == 256 Hz,
    maps channels to active_channels, drops duplicates / dummy channels,
    and returns:
        data: numpy array of shape (num_channels, num_samples) in float32
        info: dict with sampling rate, duration, file metadata
    """
    f = pyedflib.EdfReader(str(edf_path))
    try:
        n_channels = f.signals_in_file
        signal_labels = [f.getLabel(i).strip().replace("EEG ", "").replace("-REF", "") for i in range(n_channels)]
        
        # Verify sampling rates
        rates = [f.getSampleFrequency(i) for i in range(n_channels)]
        for r in rates:
            if int(r) != FS:
                raise ValueError(f"Sampling frequency {r} != expected {FS} Hz in {edf_path}")

        # Map channel indices
        # In case of duplicate names (e.g. T8-P8 appearing twice), map to the first unique occurrence
        channel_map = {}
        for idx, lbl in enumerate(signal_labels):
            if lbl in active_channels and lbl not in channel_map:
                channel_map[lbl] = idx

        missing = [c for c in active_channels if c not in channel_map]
        if missing:
            raise KeyError(f"Missing required channels in {edf_path}: {missing}")

        num_samples = f.getNSamples()[0]
        data = np.zeros((len(active_channels), num_samples), dtype=np.float32)

        for out_idx, ch_name in enumerate(active_channels):
            file_ch_idx = channel_map[ch_name]
            data[out_idx, :] = f.readSignal(file_ch_idx)

        info = {
            "num_channels": len(active_channels),
            "num_samples": num_samples,
            "duration_sec": num_samples / FS,
            "fs": FS,
            "channels": active_channels
        }
        return data, info
    finally:
        f.close()
