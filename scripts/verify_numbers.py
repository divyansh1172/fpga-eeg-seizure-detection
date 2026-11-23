"""
Verification script - READ ONLY, no files modified.
Checks all contested numbers against raw CSV data.
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path("D:/Sem/Sem-3/EE2000 Project")
SEP = "=" * 70

# ── 1. Baseline latency stats ─────────────────────────────────────────
print(SEP)
print("1. BASELINE LATENCY STATS (baseline_metrics.csv)")
print(SEP)
df = pd.read_csv(ROOT / "results/baseline_metrics.csv")
all_lats = []
for l in df["latencies"]:
    all_lats.extend(eval(l))
all_lats_np = np.array(all_lats)
print(f"All {len(all_lats_np)} individual latencies: {sorted(all_lats_np.tolist())}")
print(f"  Pooled mean         : {all_lats_np.mean():.4f} s")
print(f"  Pooled median       : {np.median(all_lats_np):.1f} s")
print(f"  Sample SD (ddof=1)  : {all_lats_np.std(ddof=1):.4f} s")
print(f"  Pop SD    (ddof=0)  : {all_lats_np.std(ddof=0):.4f} s")
print()
for _, row in df.iterrows():
    lats = eval(row["latencies"])
    print(f"  {row['subject']}: latencies={lats}, mean={np.mean(lats):.2f}, median={np.median(lats):.1f}")

# ── 2. Window count ───────────────────────────────────────────────────
print()
print(SEP)
print("2. WINDOW COUNT (baseline_folds.csv)")
print(SEP)
folds = pd.read_csv(ROOT / "results/baseline_folds.csv")
total_windows = folds["total_windows"].sum()
total_nshrs   = df["non_seizure_hours"].sum()
print(f"  Sum of total_windows in baseline_folds.csv: {total_windows}")
print(f"  Sum of non_seizure_hours in baseline_metrics.csv: {total_nshrs:.4f} h")
print(f"  Report §2.1 claims: 169,451  (correct is {total_windows})")

# ── 3. chb01_03 latency from folds ───────────────────────────────────
print()
print(SEP)
print("3. chb01_03.edf LATENCY (baseline_folds.csv)")
print(SEP)
row_03 = folds[folds["held_out_record"].str.contains("chb01_03")]
print(row_03[["subject","held_out_record","num_seizures","detected_seizures","latencies"]].to_string())
print()
print("  Report §7.3 / Fig1 caption now claims latency = 1.0 s (alarm at t=2997 s)")
print("  CSV says latency = ? (see above)")

# ── 4. k=1 sensitivity check ─────────────────────────────────────────
print()
print(SEP)
print("4. k=1 SENSITIVITY (ablation_table.csv)")
print(SEP)
abl = pd.read_csv(ROOT / "results/ablation_table.csv")
k_rows = abl[abl["ablation_type"] == "k_sweep"]
print(k_rows[["param_value","sensitivity","fa_per_hour","median_latency_sec"]].to_string(index=False))
print()
print("  At k=1, sensitivity = ", k_rows[k_rows["param_value"]==1]["sensitivity"].values[0])
print("  At k=3, sensitivity = ", k_rows[k_rows["param_value"]==3]["sensitivity"].values[0])
print("  Logically k=1 should be >= k=3 sensitivity. Check if true ↑")

# ── 5. k=1 cross with Shoeb replication number (88.2%) ───────────────
print()
print(SEP)
print("5. SHOEB REPLICATION (shoeb_replication.csv)")
print(SEP)
sh = pd.read_csv(ROOT / "results/shoeb_replication.csv")
tot_sz  = sh["total_seizures"].sum()
tot_det = sh["detected_seizures"].sum()
fa_hr   = sh["false_alarms"].sum() / sh["non_seizure_hours"].sum()
print(f"  Shoeb pooled sensitivity: {tot_det}/{tot_sz} = {tot_det/tot_sz*100:.1f}%")
print(f"  Shoeb pooled FA/h: {fa_hr:.3f}")
print(f"  k=1 ablation sensitivity: {k_rows[k_rows['param_value']==1]['sensitivity'].values[0]*100:.1f}%")
print("  --> Both are 88.2%? Coincidence or copy error or refractory masking?")

# ── 6. Shoeb per-fold missed seizures ─────────────────────────────────
print()
print(SEP)
print("6. SHOEB PER-FOLD — missed seizures in chb01")
print(SEP)
# Note: shoeb_replication.csv is subject-level, not fold-level
# Check if per-fold Shoeb CSV exists
shoeb_fold = ROOT / "results" / "shoeb_folds.csv"
if shoeb_fold.exists():
    sf = pd.read_csv(shoeb_fold)
    chb01_sf = sf[(sf["subject"]=="chb01") & (sf["total_seizures"]>0)]
    print(chb01_sf[["held_out_record","total_seizures","detected_seizures","latencies"]].to_string())
else:
    print("  shoeb_folds.csv does NOT exist — per-fold Shoeb breakdown is unavailable.")
    print("  §6.2 naming 'chb01_04 and chb01_15' as missed records is UNSUPPORTED.")
    print()
    print("  We can infer from baseline_folds.csv which chb01 records have num_seizures>0:")
    chb01_folds = folds[(folds["subject"]=="chb01") & (folds["num_seizures"]>0)]
    print(chb01_folds[["held_out_record","num_seizures","detected_seizures","latencies"]].to_string())

# ── 7. RTL testbenches in zip ─────────────────────────────────────────
print()
print(SEP)
print("7. RTL TESTBENCH FILES ON DISK")
print(SEP)
import zipfile
rtl_dir = ROOT / "rtl"
zip_path = ROOT / "mtr-15.zip"
new_tbs  = ["tb_svm_classifier.v", "tb_alarm_logic.v", "tb_uart_rx.v"]
for tb in new_tbs:
    p = rtl_dir / tb
    print(f"  {tb}: on disk = {p.exists()}")
with zipfile.ZipFile(zip_path) as z:
    names = z.namelist()
for tb in new_tbs:
    in_zip = any(tb in n for n in names)
    print(f"  {tb}: in zip  = {in_zip}")

# ── 8. Table 3 latency claim ──────────────────────────────────────────
print()
print(SEP)
print("8. TABLE 3 LATENCY — search in tex")
print(SEP)
tex = (ROOT / "report/mtr-15.tex").read_text(encoding="utf-8")
import re
# find lines around 'tab:replication_comparison' or table with 4.0 s
lines = tex.splitlines()
for i, line in enumerate(lines):
    if "4.0" in line and ("s \\\\" in line or "s\\\\") and i > 500 and i < 600:
        print(f"  Line {i+1}: {line.strip()}")

# ── 9. D2 percentage ─────────────────────────────────────────────────
print()
print(SEP)
print("9. D2 PERCENTAGE CHECK")
print(SEP)
print("  Baseline: 4 bands x 22 channels x 2 features = 176 features")
print("  With D2:  5 bands x 22 channels x 2 features = 220 features")
print(f"  Adding D2: increase = {(220-176)/176*100:.1f}%  (report says 25%)")
print(f"  Dropping D2: reduction = {(220-176)/220*100:.1f}%  (report says 20%)")

print()
print(SEP)
print("VERIFICATION COMPLETE — NO FILES MODIFIED")
print(SEP)
