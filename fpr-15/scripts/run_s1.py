"""
Runner script for Step S1: Subject selection, rule evaluation, and manifest generation.
"""

import sys
from pathlib import Path

# Add project root to path
PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJ_ROOT))

from src.data_io import evaluate_subject_rules, build_manifest
from src.config import DATA_DIR, MANIFEST_PATH

def main():
    summaries_dir = PROJ_ROOT
    print("Evaluating subject selection rule across CHB-MIT...")
    rules_res, selected = evaluate_subject_rules(summaries_dir)

    print(f"\nMechanical rule selection result:")
    print(f"Selected first 3 eligible cases: {selected}")
    
    print("\nCase-by-case evaluation (first 10):")
    for r in rules_res[:10]:
        case = r["case"]
        status = r["status"]
        sz = r["seizures"]
        ch = r["channels"]
        reason = r["reason"]
        print(f"  {case}: {status} (seizures={sz}, channels={ch}) -> {reason}")

    print("\nConstructing frozen data/manifest.csv...")
    df = build_manifest(summaries_dir, target_seizure_free_hours=10)
    print(f"Manifest written to: {MANIFEST_PATH}")
    print(f"Total files in manifest: {len(df)}")

    print("\nPer-subject breakdown in manifest:")
    for sub in selected:
        sub_df = df[df["subject"] == sub]
        sz_files = sub_df[sub_df["is_seizure_file"] == 1]
        sz_free = sub_df[sub_df["is_seizure_file"] == 0]
        total_sz = sz_files["num_seizures"].sum()
        print(f"  {sub}:")
        print(f"    Seizure files: {len(sz_files)} files containing {total_sz} annotated seizures")
        print(f"    Seizure-free background files: {len(sz_free)} files (~{len(sz_free)} hours)")
        print(f"    Total files for subject: {len(sub_df)}")

    # Print download commands
    print("\n" + "="*70)
    print("DOWNLOAD COMMANDS FOR SELECTED DATASET")
    print("="*70)
    print("Wget commands (or Python equivalent):")
    for _, row in df.iterrows():
        sub = row["subject"]
        fname = row["filename"]
        print(f"wget -c https://physionet.org/files/chbmit/1.0.0/{sub}/{fname} -P data/raw/{sub}/")

if __name__ == "__main__":
    main()
