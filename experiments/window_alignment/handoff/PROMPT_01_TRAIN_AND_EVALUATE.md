# COLLABORATOR EXECUTION PROMPT 01: TRAINING & LORO CROSS-VALIDATION EVALUATION

**Instruction for Collaborator:** Copy and paste this prompt in its entirety into your Antigravity AI assistant after completing `PROMPT_00_ENVIRONMENT_AND_METHODOLOGY.md`.

---

```markdown
# TASK: EXECUTE LORO TRAINING AND COMPARATIVE EVALUATION (1.0s vs 2.0s WINDOWS)

## 0. YOUR ROLE
You are acting as a Senior Machine Learning Systems Engineer and Biomedical DSP Specialist.
Your objective is to execute patient-specific Leave-One-Record-Out (LORO) cross-validation training and clinical event evaluation across all 47 recordings of patients `chb01`, `chb02`, and `chb03` under two distinct configurations:
1. **Configuration A (`window_1s`):** 1.0-second non-overlapping windows ($W=256, H=256$ samples at $256\text{ Hz}$). Intended for native FPGA hardware compatibility.
2. **Configuration B (`window_2s`):** 2.0-second 50% overlapping windows ($W=512, H=256$ samples at $256\text{ Hz}$). Reproduces the historical software baseline.

---

## 1. SCIENTIFIC METHODOLOGY & ANTI-LEAKAGE INVARIANTS

You must adhere strictly to these clinical machine learning standards:
1. **Zero Data Leakage:**
   - Standardization parameters ($\mu, \sigma$) must be fitted **exclusively on the training portion** of each fold:
     ```python
     X_train_scaled = scaler.fit_transform(X_train)
     X_test_scaled = scaler.transform(X_test)
     ```
   - Never fit scalers on the held-out test record.
   - Never randomly partition windows into train/test sets. Cross-validation is partitioned strictly at the independent whole-recording level.
2. **Class Imbalance Mitigation:**
   - Seizure windows account for $<2\%$ of total recording duration. The classifier must use `class_weight='balanced'` with $C=1.0$.
3. **Temporal Post-Processing:**
   - Raw window decisions must pass through $k=3$ consecutive window persistence.
   - Alarms occurring within $30.0\text{ seconds}$ of an active alarm must be merged under the refractory period lockout.
4. **Clinical Event Scoring:**
   - An annotated seizure $[onset, offset]$ is marked detected if an alarm timestamp falls within $[onset - 2.0\text{s}, offset]$.
   - Detection latency is $\tau = t_{\text{alarm}} - onset$.
   - Any alarm outside all valid seizure detection intervals counts as a False Alarm.
   - False Alarm Rate (FAR) is normalized by non-seizure recording hours:
     $$\text{FAR} = \frac{\text{Total False Alarms}}{\text{Total Non-Seizure Hours}}$$

---

## 2. STEP-BY-STEP EXECUTION INSTRUCTIONS

### Step 1: Execute Configuration A (1.0-Second FPGA-Aligned Windows)
Run the central experiment runner for Configuration A across all subjects:
```bash
python3 experiments/window_alignment/code/experiment_runner.py --config 1s --subject all
```
**What this does:**
- Extracts 176 features ($22\text{ ch}\times 4\text{ bands}\times 2\text{ feats}$) on 1.0s non-overlapping windows.
- Executes 47 LORO folds:
  - `chb01`: 17 folds
  - `chb02`: 13 folds
  - `chb03`: 17 folds
- Fits `SimpleStandardScaler` on training windows only.
- Trains `LinearSVC(C=1.0, class_weight='balanced')`.
- Evaluates event metrics (Sensitivity, FA/h, Latency) on held-out records.
- Saves fold models into `experiments/window_alignment/artifacts/window_1s_fpga_aligned/models/`.
- Trains and saves full-dataset candidate deployment models.
- Generates `experiments/window_alignment/reports/window_1s_fpga_aligned/loro_folds.csv` and `summary_metrics.csv`.

### Step 2: Execute Configuration B (2.0-Second Baseline Windows)
Run the central experiment runner for Configuration B across all subjects:
```bash
python3 experiments/window_alignment/code/experiment_runner.py --config 2s --subject all
```
**What this does:**
- Extracts 176 features on 2.0s overlapping windows (50% overlap, 1.0s hop).
- Executes 47 LORO folds under the exact same zero-leakage protocol.
- Generates `experiments/window_alignment/reports/window_2s_software_baseline/loro_folds.csv` and `summary_metrics.csv`.

### Step 3: Compile Side-by-Side Comparison Report
Create a comparative analysis script or command to consolidate the results:
```bash
python3 -c "
import json
import csv
from pathlib import Path

rep_dir = Path('experiments/window_alignment/reports')
s1_path = rep_dir / 'window_1s_fpga_aligned' / 'summary_metrics.json'
s2_path = rep_dir / 'window_2s_software_baseline' / 'summary_metrics.json'

with open(s1_path) as f1, open(s2_path) as f2:
    d1 = json.load(f1)['subjects']
    d2 = json.load(f2)['subjects']

print('=' * 80)
print(' COMPARATIVE RESULTS: CONFIGURATION A (1.0s) vs CONFIGURATION B (2.0s)')
print('=' * 80)
print(f'{\"Subject\":8s} | {\"Config A Sens\":14s} | {\"Config B Sens\":14s} | {\"Config A FA/h\":14s} | {\"Config B FA/h\":14s}')
print('-' * 80)

for sub1, sub2 in zip(d1, d2):
    sub = sub1['subject']
    s1_str = f\"{sub1['detected_seizures']}/{sub1['total_seizures']} ({sub1['seizure_sensitivity']*100:.1f}%)\"
    s2_str = f\"{sub2['detected_seizures']}/{sub2['total_seizures']} ({sub2['seizure_sensitivity']*100:.1f}%)\"
    fa1_str = f\"{sub1['false_alarms_per_hour']:.3f} ({sub1['total_false_alarms']} FA)\"
    fa2_str = f\"{sub2['false_alarms_per_hour']:.3f} ({sub2['total_false_alarms']} FA)\"
    print(f'{sub:8s} | {s1_str:14s} | {s2_str:14s} | {fa1_str:14s} | {fa2_str:14s}')
print('=' * 80)
"
```

Save the comparative metrics table to:
`experiments/window_alignment/reports/comparison_1s_vs_2s.csv`

---

## 3. STRICT CONSTRAINTS & PROHIBITIONS

- Do NOT overwrite existing baseline files in `results/baseline_folds.csv` or `results/models/`.
- Do NOT fabricate or alter any cross-validation numbers. Every reported percentage must include exact denominators (e.g., $17/17\text{ seizures}$, $X\text{ FA} / Y\text{ hours}$).
- Do NOT use held-out test windows to tune hyperparameters.
- Do NOT modify the active FPGA RTL.

---

## 4. REPORT DELIVERABLE REQUIRED

Upon completion of this prompt, report:
1. **Execution Status:** Confirmation that both Configuration A (1.0s) and Configuration B (2.0s) completed all 47 folds.
2. **Cohort-Level Summary Table:**
   - Total Seizures Evaluated and Detected (with exact denominators).
   - Event Sensitivity (%).
   - Total False Alarms and Non-Seizure Hours.
   - False Alarm Rate (FA/hour).
   - Median and Mean Latency ($\tau$ in seconds).
3. **Key Finding:** Does retraining the Linear SVM directly on 1.0-second windows maintain sensitivity and clinical viability compared to the 2.0-second baseline?
4. **Transition Statement:** `PROMPT_01_TRAIN_AND_EVALUATE COMPLETE. PROCEED TO PROMPT_02_FIXED_POINT_AND_FPGA_EXPORT`.
```
