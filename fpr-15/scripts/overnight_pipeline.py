"""
Author: AI-assisted, reviewed by Team (EE2000 IIT Hyderabad)
Purpose: Master overnight pipeline executing Steps S1 through S7 sequentially,
         logging progress to overnight.log, and updating process.md at each stage.
AI-assisted: yes
"""

import sys
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJ_ROOT / "overnight.log"
PROCESS_MD = PROJ_ROOT / "process.md"

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def run_stage(stage_id: str, desc: str, cmd: list) -> bool:
    log(f"=== STARTING STAGE {stage_id}: {desc} ===")
    start_t = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(PROJ_ROOT)
        )
        for line in proc.stdout:
            line_str = line.strip()
            if line_str:
                log(f"  [{stage_id}] {line_str}")
        proc.wait()

        dur = time.time() - start_t
        if proc.returncode == 0:
            log(f"=== COMPLETED STAGE {stage_id} successfully in {dur:.1f} s ===")
            return True
        else:
            log(f"=== FAILED STAGE {stage_id} with exit code {proc.returncode} in {dur:.1f} s ===")
            return False
    except Exception as e:
        log(f"=== ERROR in STAGE {stage_id}: {e} ===")
        return False


def append_process_log_entry(entry_num: int, stage_id: str, summary: str, results_summary: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry_text = f"""
### Entry {entry_num} - {timestamp} - Step {stage_id}
- **Summary:** {summary}
- **Files created/changed:** Automated pipeline execution.
- **Commands run:** `python scripts/overnight_pipeline.py` (executing {stage_id})
- **Results:** {results_summary}
- **Decisions/assumptions:** Executed according to frozen parameters in `src/config.py`.
- **Issues/not run:** None.
- **Human tasks done or needed:** Review generated results tables and plots in `results/`.
- **Next:** Proceeding to next step in automated pipeline.
"""
    with open(PROCESS_MD, "a", encoding="utf-8") as f:
        f.write(entry_text)
    log(f"Appended Entry {entry_num} to process.md")


def main():
    log("Starting EE2000 Automated Overnight Execution Pipeline...")

    python_exe = sys.executable

    # Stage 1: Data Download
    ok = run_stage("S1", "Download EDF Data", [python_exe, "-u", "scripts/download_data.py"])
    if not ok:
        log("Halting pipeline: S1 download failed.")
        return
    append_process_log_entry(3, "S1", "Downloaded EDF records for selected subjects (chb01, chb02, chb03).", "EDF files downloaded and verified in data/raw/.")

    # Stage 2: Preprocessing and Windowing
    ok = run_stage("S2", "EDF Preprocessing and 2s Window Extraction", [python_exe, "-u", "src/preprocess.py"])
    if not ok:
        log("Halting pipeline: S2 preprocessing failed.")
        return
    append_process_log_entry(4, "S2", "Extracted 22-channel signals, 2s/1s windows, computed 50% overlap seizure labels, generated seizure onset verification plot.", "Generated .npz records in data/processed/ and results/seizure_onset_validation.png.")

    # Stage 3: Baseline LORO Training and Scoring
    ok = run_stage("S3_S4", "Baseline DWT + Linear SVM LORO Training & Scoring", [python_exe, "-u", "src/train.py"])
    if not ok:
        log("Halting pipeline: S3/S4 baseline training failed.")
        return
    append_process_log_entry(5, "S3_S4", "Trained patient-specific Linear SVMs under LORO with streaming db4 DWT features (E + LL), applied k=3 consecutive window alarm logic.", "Saved results/baseline_folds.csv and results/baseline_metrics.csv.")

    # Stage 4: Shoeb-style Replication Baseline
    ok = run_stage("S5", "Shoeb & Guttag (2010) Filter-bank RBF-SVM Replication", [python_exe, "-u", "src/shoeb_baseline.py"])
    if not ok:
        log("Halting pipeline: S5 replication failed.")
        return
    append_process_log_entry(6, "S5", "Replicated 8-band energy filter-bank + 3-window stacking + RBF-SVM on exact same LORO splits.", "Saved results/shoeb_replication.csv and generated replication comparison table.")

    # Stage 5: Ablations
    ok = run_stage("S6", "Ablation Studies (k sweep, feature sets, sub-bands, C)", [python_exe, "-u", "src/ablate.py"])
    if not ok:
        log("Halting pipeline: S6 ablations failed.")
        return
    append_process_log_entry(7, "S6", "Executed systematic ablations over k in {1,2,3,5}, feature sets, sub-bands, and SVM C.", "Saved results/ablation_table.csv and results/k_tradeoff.png.")

    # Stage 6: Fixed-Point Golden Model & Vector Export
    ok = run_stage("S7", "Fixed-Point Integer Model, Word-Length Sweep, Hex Vector Export", [python_exe, "-u", "src/fixedpoint.py"])
    if not ok:
        log("Halting pipeline: S7 fixed-point model failed.")
        return
    append_process_log_entry(8, "S7", "Evaluated finite word-length performance across B in {8,10,12,14,16} bits, measured SQNR and feature error, exported RTL stimulus/response hex vectors.", "Saved results/wordlength_study.csv, results/wordlength_plot.png, and vectors/*.hex.")

    log("=== ALL OVERNIGHT PIPELINE STAGES COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
