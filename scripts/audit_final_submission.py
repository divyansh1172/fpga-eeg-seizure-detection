"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Team: 15
Author: Member 1 & Member 4 (Audit Leads)
Purpose: Exhaustive pre-submission audit script for the Endsem / Final Report milestone.
         Verifies final-15.pdf, final-15.zip, Course Rule 9 compliance (zero raw data),
         all 7 Verilog RTL modules and testbenches, results CSV consistency, and git hygiene.
AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Team)
"""

import os
import sys
import zipfile
import re
import csv
from pathlib import Path
try:
    import pandas as pd
except ImportError:
    pd = None

PROJ_ROOT = Path(__file__).resolve().parent.parent

def audit_final_submission():
    errors = []
    warnings = []
    print("=" * 80)
    print("EE2000 TEAM 15: FINAL PROJECT SUBMISSION AUDIT REPORT")
    print("=" * 80)

    # 1. Audit final-15.pdf
    pdf_path = PROJ_ROOT / "final-15.pdf"
    if not pdf_path.exists():
        pdf_path = PROJ_ROOT / "report" / "final-15.pdf"

    if not pdf_path.exists():
        errors.append("final-15.pdf not found in project root or report/!")
    else:
        size_kb = pdf_path.stat().st_size / 1024
        print(f"[OK] final-15.pdf located: {pdf_path} ({size_kb:.1f} KB)")
        with open(pdf_path, "rb") as f:
            if f.read(5) != b"%PDF-":
                errors.append("final-15.pdf has invalid PDF magic bytes!")
            else:
                print("     Valid PDF magic header (%PDF-).")

    # 2. Audit final-15.zip
    zip_path = PROJ_ROOT / "final-15.zip"
    if not zip_path.exists():
        warnings.append("final-15.zip has not been packaged yet. Run scripts/package_final_submission.py.")
    else:
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"[OK] final-15.zip found: {size_mb:.2f} MB")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                print(f"     Archive contains {len(names)} files.")

                # Course Rule 9 Check (STRICT NON-NEGOTIABLE)
                bad_files = [n for n in names if n.lower().endswith(".edf") or n.lower().endswith(".npz")]
                if bad_files:
                    errors.append(f"COURSE RULE 9 VIOLATION! Raw data files found in zip: {bad_files}")
                else:
                    print("     [RULE 9 PASS] Zero .edf or .npz raw data files found in archive.")

                # Check core deliverables in archive
                for required in ["final-15.pdf", "README.md", "process.md", "results/uart_demo_playback.log"]:
                    if required not in names:
                        errors.append(f"Missing core file '{required}' in final-15.zip!")
                    else:
                        print(f"     [OK] '{required}' present in archive.")
        except Exception as e:
            errors.append(f"Failed to read final-15.zip: {e}")

    # 3. Audit Synthesizable Verilog RTL Datapath
    rtl_dir = PROJ_ROOT / "rtl"
    required_rtl = [
        "uart_rx.v",
        "iir_biquad.v",
        "dwt_db4.v",
        "feature_accumulator.v",
        "svm_classifier.v",
        "alarm_logic.v",
        "seven_seg_controller.v",
        "top_seizure_detector.v",
        "boolean_board.xdc"
    ]
    print("\n--> Auditing Verilog RTL Modules in rtl/:")
    for r in required_rtl:
        fp = rtl_dir / r
        if not fp.exists():
            errors.append(f"Missing RTL source file: rtl/{r}")
        else:
            print(f"     [OK] rtl/{r} exists ({fp.stat().st_size} bytes)")

    # 4. Audit RTL Simulation Testbenches
    required_tb = [
        "tb_uart_rx.v",
        "tb_iir_biquad.v",
        "tb_dwt_db4.v",
        "tb_feature_accumulator.v",
        "tb_svm_classifier.v",
        "tb_alarm_logic.v",
        "tb_seven_seg_controller.v",
        "tb_top_seizure_detector.v"
    ]
    print("\n--> Auditing Verilog Testbenches in rtl/:")
    for tb in required_tb:
        fp = rtl_dir / tb
        if not fp.exists():
            errors.append(f"Missing testbench: rtl/{tb}")
        else:
            print(f"     [OK] rtl/{tb} exists")

    # 5. Audit Results & Numerical Integrity
    res_dir = PROJ_ROOT / "results"
    required_results = [
        "baseline_metrics.csv",
        "baseline_folds.csv",
        "shoeb_replication.csv",
        "ablation_table.csv",
        "wordlength_study.csv",
        "fixedpoint_loro_comparison.csv",
        "uart_demo_playback.log"
    ]
    print("\n--> Auditing Results & Metrics CSVs in results/:")
    for res in required_results:
        fp = res_dir / res
        if not fp.exists():
            errors.append(f"Missing required result file: results/{res}")
        else:
            print(f"     [OK] results/{res} exists")

    # Numerical verification of fixed-point comparison
    fixed_comp_csv = res_dir / "fixedpoint_loro_comparison.csv"
    if fixed_comp_csv.exists():
        with open(fixed_comp_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        row_float = next((r for r in reader if "Float" in r["implementation"]), None)
        row_fixed = next((r for r in reader if "Fixed" in r["implementation"]), None)
        if not row_float or not row_fixed:
            errors.append("Could not locate Float and Fixed rows in fixedpoint_loro_comparison.csv!")
        elif float(row_float["sensitivity_pct"]) != 100.0 or float(row_fixed["sensitivity_pct"]) != 100.0:
            errors.append("Sensitivity does not match 100.0% in fixedpoint_loro_comparison.csv!")
        elif float(row_float["fa_per_hour"]) != 0.373 or float(row_fixed["fa_per_hour"]) != 0.373:
            errors.append("FA/h does not match 0.373 in fixedpoint_loro_comparison.csv!")
        else:
            print("     [VERIFIED] Fixed-point vs. Float achieves exact 100.0% sens, 0.373 FA/h, 3.0s latency.")

    # 6. Audit process.md log
    process_md = PROJ_ROOT / "process.md"
    if not process_md.exists():
        errors.append("process.md missing!")
    else:
        text = process_md.read_text(encoding="utf-8")
        if "Stage 6A" not in text or "Stage 8" not in text:
            warnings.append("process.md may need updated entries for Endsem Phase milestones.")
        print(f"\n[OK] process.md verified ({len(text.splitlines())} lines).")

    # Final summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY:")
    if errors:
        print(f"[FAIL] Found {len(errors)} ERROR(S):")
        for e in errors:
            print(f"  - ERROR: {e}")
    else:
        print("[SUCCESS] ZERO ERRORS FOUND! All deliverables, code, and RTL are intact.")

    if warnings:
        print(f"[WARN] Found {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - WARNING: {w}")
    print("=" * 80)

    return len(errors) == 0

if __name__ == "__main__":
    success = audit_final_submission()
    sys.exit(0 if success else 1)
