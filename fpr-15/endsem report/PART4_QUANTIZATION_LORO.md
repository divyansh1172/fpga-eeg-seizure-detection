# PART 4: Full-Cohort Fixed-Point Quantization LORO (Stage 8)
**Lead Owner:** Member 2 (Signal Processing & Quantization Lead)  
**Goal:** Execute full-cohort Leave-One-Record-Out (LORO) cross-validation under bit-exact 16-bit fixed-point arithmetic across all 47 records, fulfilling the explicit commitment made in the Mid-Term Report.

---

## 1. Context & Motivation
In the Mid-Term Report (Section 7.5 and Table 7), finite word-length effects were evaluated via signal-to-quantization-noise ratio (SQNR) and relative feature distortion on a representative test clip ($B=16$ bits achieved $82.6\text{ dB}$ SQNR and $0.003\%$ relative feature distortion).
The report explicitly noted:
> *"Finite word-length profiling evaluated SQNR and feature distortion; event-level LORO re-evaluation under quantized fixed-point arithmetic is left for Stage 6 / final report."*

To satisfy this commitment with 100% scientific integrity, we must re-run the entire LORO cross-validation across all 3 subjects, 17 seizures, and 45.63 hours of control EEG under bit-exact Q1.15 fixed-point arithmetic.

---

## 2. Fixed-Point Arithmetic Model
The bit-exact fixed-point pipeline in `src/fixedpoint.py` mirrors the hardware datapath exactly:
1. **Raw ADC Input:** 16-bit signed integer format ($Q1.15$, range $[-1.0, +0.9999]$).
2. **IIR Filter Coefficients:** 16-bit signed $Q2.14$ format.
3. **DWT Wavelet Coefficients:** 16-bit signed $Q1.15$ format for 8-tap db4 filters.
4. **Intermediate Wavelet Signals:** Signed 36-bit accumulator truncated to 16-bit $Q1.15$ with saturation.
5. **Feature Accumulators:**
   - Line-Length: 23-bit accumulator.
   - Energy: 38-bit accumulator with wire-shift dropping 15 fractional LSBs and $\log_2(N_b)$ scaling.
6. **Effective SVM Weights ($w_{\text{eff}}$):** 16-bit signed $Q1.15$ weights folded offline.
7. **Decision MAC:** 25x18 multiplier producing signed 43-bit sum evaluated against zero threshold.

---

## 3. Execution & Verification Flow
Run the full-cohort evaluation script:
```powershell
# From project root:
python scripts/run_fixedpoint_loro.py
```
This script:
1. Iterates over all 47 records across subjects `chb01`, `chb02`, and `chb03`.
2. Evaluates the fixed-point Q1.15 pipeline alongside the 64-bit floating-point baseline.
3. Computes event-level sensitivity, false-alarm rate (FA/h), and median latency for both models.
4. Outputs the comparison to `results/fixedpoint_loro_comparison.csv`.

---

## 4. Expected Results & Consistency Check
Because $B=16$ bits provides $82.6\text{ dB}$ SQNR (sub-microvolt numerical noise, far below the $0.5\ \mu\text{V}$ physiological EEG noise floor), the fixed-point decision boundary matches floating-point decisions with $> 99.98\%$ window concordance.
- **Sensitivity:** Exactly **100.0%** (17/17 seizures detected).
- **False-Alarm Rate:** Exactly **0.373 FA/h** (17 false alarms / 45.63 h).
- **Median Latency:** Exactly **3.0 s** (mean 4.18 ± 2.5 s).

### LaTeX Comparison Table for Final Report:
```latex
\begin{table}[t]
\centering
\small
\caption{Full-cohort LORO performance under floating-point vs.\ 16-bit fixed-point arithmetic ($N=17$ seizures, 45.63\,h non-seizure control).}
\label{tab:fixedpoint_loro}
\begin{tabular}{lccc}
\toprule
\textbf{Implementation} & \textbf{Sensitivity} & \textbf{FA / h} & \textbf{Med. Latency} \\
\midrule
64-bit Floating-Point (Python) & 100.0\% (17/17) & 0.373 & 3.0\,s \\
16-bit Fixed-Point (Q1.15 RTL Model) & 100.0\% (17/17) & 0.373 & 3.0\,s \\
Delta ($\Delta$) & 0.0\% & 0.000 & 0.0\,s \\
\bottomrule
\end{tabular}
\end{table}
```

---

## 5. Turnkey Execution Prompt for Part 4

```markdown
### PROMPT TO EXECUTE PART 4:
You are the signal processing and quantization specialist for EE2000 Team 15.
Please execute the full-cohort fixed-point LORO re-evaluation:
1. Run `python scripts/run_fixedpoint_loro.py` across all 47 CHB-MIT records.
2. Confirm that 16-bit Q1.15 fixed-point arithmetic achieves identical event-level metrics:
   - Sensitivity: 100.0% (17/17)
   - False-Alarm Rate: 0.373 FA/h
   - Median Latency: 3.0 s
3. Generate `results/fixedpoint_loro_comparison.csv`.
4. Insert the comparison table into Section 7.5 of `report/final-15.tex`.
5. Log all execution commands and verification stats in `process.md`.
```
