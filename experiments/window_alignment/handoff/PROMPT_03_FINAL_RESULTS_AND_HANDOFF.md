# COLLABORATOR EXECUTION PROMPT 03: FINAL RESULTS CONSOLIDATION & HANDOFF

**Instruction for Collaborator:** Copy and paste this prompt in its entirety into your Antigravity AI assistant after completing `PROMPT_02_FIXED_POINT_AND_FPGA_EXPORT.md`.

---

```markdown
# TASK: FINAL RESULTS CONSOLIDATION, COMPARATIVE REPORT, AND ARTIFACT PACKAGING

## 0. YOUR ROLE
You are acting as the Lead Research Software Architect, Technical Documentation Lead, and Machine Learning Systems Auditor.

Your objective is to consolidate all experimental data generated across Prompts 00, 01, and 02 into a publication-grade final comparative report, certify all exported FPGA model candidate artifacts, document all completed and failed runs, and package the complete delivery for seamless review.

---

## 1. COMPREHENSIVE CONSOLIDATION CHECKLIST

Ensure the following data files and model artifacts exist and have been validated:
1. `experiments/window_alignment/reports/window_1s_fpga_aligned/loro_folds.csv` (All 47 folds)
2. `experiments/window_alignment/reports/window_1s_fpga_aligned/summary_metrics.csv`
3. `experiments/window_alignment/reports/window_1s_fpga_aligned/fixedpoint_comparison.csv`
4. `experiments/window_alignment/reports/window_2s_software_baseline/loro_folds.csv` (All 47 folds)
5. `experiments/window_alignment/reports/window_2s_software_baseline/summary_metrics.csv`
6. `experiments/window_alignment/reports/comparison_1s_vs_2s.csv`
7. Validated candidate model directories in `experiments/window_alignment/artifacts/candidate_models/`:
   - `chb01_candidate_1s/`
   - `chb02_candidate_1s/`
   - `chb03_candidate_1s/`

---

## 2. GENERATE FINAL REPORT: `FINAL_WINDOW_ALIGNMENT_REPORT.md`

Generate the comprehensive final report at:
`experiments/window_alignment/reports/FINAL_WINDOW_ALIGNMENT_REPORT.md`

The report must include the following mandatory sections:

### Section 1: Executive Summary
- Brief statement of the experiment goal: investigating and resolving the temporal window mismatch between 2.0-second software training and 1.0-second Spartan-7 FPGA hardware inference.
- High-level conclusion: Did retraining the Linear SVM directly on 1.0-second non-overlapping windows maintain clinical seizure sensitivity while achieving true hardware compatibility?

### Section 2: Full Clinical Performance Comparison (With Exact Denominators)
Provide a complete markdown table comparing Configuration A (1.0s FPGA-aligned) vs. Configuration B (2.0s Software baseline):

| Cohort / Patient | Metric | Configuration A (1.0s Window) | Configuration B (2.0s Window) | Difference / Delta |
| :--- | :--- | :--- | :--- | :--- |
| **chb01** | Seizure Sensitivity | $X_1 / Y_1$ ($P_1\%$) | $X_2 / Y_2$ ($P_2\%$) | $\Delta P\%$ |
| | False Alarm Rate | $F_1 / H_1\text{ h}$ ($R_1\text{ FA/h}$) | $F_2 / H_2\text{ h}$ ($R_2\text{ FA/h}$) | $\Delta R\text{ FA/h}$ |
| | Median Latency ($\tau$) | $M_1\text{ s}$ | $M_2\text{ s}$ | $\Delta M\text{ s}$ |
| **chb02** | Seizure Sensitivity | ... | ... | ... |
| | False Alarm Rate | ... | ... | ... |
| | Median Latency ($\tau$) | ... | ... | ... |
| **chb03** | Seizure Sensitivity | ... | ... | ... |
| | False Alarm Rate | ... | ... | ... |
| | Median Latency ($\tau$) | ... | ... | ... |
| **POOLED COHORT** | **Total Sensitivity** | **$X / 17$ ($P\%$)** | **$X' / 17$ ($P'\%$)** | **$\Delta P\%$** |
| | **Pooled FAR** | **$F / H\text{ h}$ ($R\text{ FA/h}$)** | **$F' / H\text{ h}$ ($R'\text{ FA/h}$)** | **$\Delta R\text{ FA/h}$** |
| | **Median Latency** | **$M\text{ s}$** | **$M'\text{ s}$** | **$\Delta M\text{ s}$** |

### Section 3: Window-Level Classification Metrics
Provide window-level binary classification performance (Sensitivity, Specificity, Precision, F1-Score, Balanced Accuracy, and ROC-AUC) for both configurations.

### Section 4: Bit-Accurate Fixed-Point Quantization Audit
Document the empirical findings from `fixedpoint_comparison.csv`:
- Overall decision agreement percentage between 64-bit float and 16-bit Q15 fixed-point RTL model across all evaluated windows.
- Mean SQNR (dB) and Maximum Absolute Score Error.
- Confirmation of anti-duplication assertion: certify that fixed-point results were generated from authentic integer simulation, not duplicated float variables.

### Section 5: FPGA Candidate Model Package Verification
Document the exported candidate deployment packages:
- Exact file paths, line counts, and checksums for `weights.mem` (176 lines) and `bias.mem` (1 line).
- Certification that each artifact passed `validation.py` with zero discrepancies.
- Scaling multiplier $S_M$ and effective bias value $b_{\text{fixed}}$ for each subject.

### Section 6: Recommended Hardware Integration Steps (Phase 3)
Outline the technical steps required to load the candidate model into the FPGA RTL:
1. Copying candidate `weights.mem` and `bias.mem` to `rtl/`.
2. Running `run_all.sh` to verify `tb_svm_classifier.v` and `tb_top_seizure_detector.v` with candidate weights.
3. Running Vivado synthesis (`scripts/run_vivado_synth.tcl`) to verify timing closure at 100 MHz on Spartan-7.

### Section 7: Scientific Limitations & Scope Disclaimer
State explicitly:
- The evaluation was conducted on a research cohort of 3 subjects (47 records, 17 seizures) from CHB-MIT.
- These results demonstrate algorithmic and fixed-point compatibility for Spartan-7 FPGA architecture, but do NOT constitute clinical validation or medical device approval.

---

## 3. EXACT LIST OF ARTIFACTS TO PACKAGE AND RETURN

Confirm that the following files are present and ready for delivery:
1. `experiments/window_alignment/reports/FINAL_WINDOW_ALIGNMENT_REPORT.md`
2. `experiments/window_alignment/reports/comparison_1s_vs_2s.csv`
3. `experiments/window_alignment/reports/window_1s_fpga_aligned/summary_metrics.json`
4. `experiments/window_alignment/reports/window_1s_fpga_aligned/fixedpoint_comparison.csv`
5. `experiments/window_alignment/reports/window_2s_software_baseline/summary_metrics.json`
6. `experiments/window_alignment/artifacts/candidate_models/chb01_candidate_1s/`
7. `experiments/window_alignment/artifacts/candidate_models/chb02_candidate_1s/`
8. `experiments/window_alignment/artifacts/candidate_models/chb03_candidate_1s/`

---

## 4. FINAL COMPLETION STATEMENT

Conclude your execution with:
`WINDOW ALIGNMENT RETRAINING AND FPGA COMPATIBILITY FRAMEWORK COMPLETE AND CERTIFIED.`
```
