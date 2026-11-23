"""
Rerun Shoeb replication with per-fold CSV logging.
Saves results/shoeb_folds.csv with one row per held-out record.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_ROOT))

from src.shoeb_baseline import run_shoeb_replication_for_subject
from src.config import SUBJECTS, RESULTS_DIR

all_folds = []
for sub in SUBJECTS:
    fold_results, _ = run_shoeb_replication_for_subject(sub)
    all_folds.extend(fold_results)

df = pd.DataFrame(all_folds)
out = RESULTS_DIR / "shoeb_folds.csv"
df.to_csv(out, index=False)
print(f"\nSaved {len(df)} fold rows -> {out}")
print(df[df['total_seizures'] > 0].to_string())
