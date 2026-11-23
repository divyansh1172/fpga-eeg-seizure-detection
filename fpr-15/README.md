# Real-Time EEG Seizure Detection on FPGA (DWT + Linear SVM)
**EE2000 Project (Team 15) — Department of Electrical Engineering, IIT Hyderabad**

[![Course Deliverable](https://img.shields.io/badge/Course-EE2000%20Fall%202026-blue.svg)](file:///D:/Sem/Sem-3/EE2000%20Project/report/mtr-15.pdf)
[![Spartan-7 FPGA](https://img.shields.io/badge/FPGA-Xilinx%20Spartan--7%20XC7S50-green.svg)](https://www.realdigital.org/hardware/boolean)
[![PhysioNet CHB-MIT](https://img.shields.io/badge/Dataset-PhysioNet%20CHB--MIT-orange.svg)](https://physionet.org/content/chbmit/1.0.0/)
[![Submission Audit](https://img.shields.io/badge/Audit-40%2F40%20Checks%20Passed-brightgreen.svg)](file:///D:/Sem/Sem-3/EE2000%20Project/scripts/audit_submission.py)

---

## 1. Executive Summary & Verified Results

This repository contains the complete software baseline, literature replication, finite word-length analysis, and synthesizable Verilog RTL for real-time epileptic seizure detection on multichannel scalp EEG. The pipeline targets the RealDigital Boolean Board (Xilinx Spartan-7 XC7S50 FPGA).

| Pipeline Configuration | Event Sensitivity | False Alarms / hr | Median Latency | Target Architecture / Platform |
| :--- | :---: | :---: | :---: | :--- |
| **Proposed DWT + Linear SVM** | **100.0% (17/17)** | **0.373 FA/h** | **3.0 s** | **Spartan-7 XC7S50 RTL (<5% logic)** |
| Replicated Shoeb (2010) \cite{shoeb2010icml} | 88.2% (15/17) | 0.307 FA/h | 5.0 s | Software RBF-SVM (528 features) |
| Published Shoeb (2010) | 96.0% (166/173) | 0.083 FA/h | 3.0 s | 24-patient cohort (916 hours) |

* **Exact 95% Clopper-Pearson CI on Sensitivity:** $[80.5\%, 100.0\%]$
* **Poisson 95% CI on False-Alarm Rate:** $[0.217, 0.597]$\,FA/h ($\approx 1$ FA every 2.68 hours)
* **Word-Length Profile:** 16-bit Q1.15 fixed-point arithmetic maintains **82.6 dB SQNR** with $<0.01\%$ feature distortion.

---

## 2. Directory Layout & Manifest

```text
EE2000 Project/
├── mtr-15.pdf             # Compiled Mid-Term Project Report (IEEE/CVF review format)
├── README.md              # Reproduction guide, directory map, and execution commands
├── process.md             # Append-only engineering log and AI interaction ledger
│
├── src/                   # End-to-end Python pipeline (data, DWT, LORO, ablations)
│   ├── config.py          # Central frozen hyperparameters and constants
│   ├── data_io.py         # PhysioNet CHB-MIT EDF reader and summary parser
│   ├── preprocess.py      # Causal 0.5-25 Hz IIR filtering and sliding window generator
│   ├── dwt.py             # 5-level Daubechies-4 (db4) discrete wavelet transform
│   ├── features.py        # Sub-band Energy (E) and Line-Length (LL) extractors
│   ├── train.py           # Patient-specific Leave-One-Record-Out (LORO) SVM trainer
│   ├── postprocess.py     # k-consecutive window persistence alarm logic
│   ├── evaluate.py        # Event-level clinical scoring (sensitivity, FA/h, latency)
│   ├── shoeb_baseline.py  # Independent replication of Shoeb & Guttag (ICML 2010)
│   ├── ablate.py          # 4-dimensional ablation sweeps (k, features, bands, C)
│   └── fixedpoint.py      # Uniform quantization sweep (8..16b) & hex vector export
│
├── rtl/                   # Synthesizable Verilog modules and verification testbenches
│   ├── dwt_db4.v          # Level-1 db4 analysis filter bank (8-tap Q1.15 MAC pair)
│   ├── svm_classifier.v   # Pipelined Linear SVM dot-product engine (176 cycles)
│   ├── alarm_logic.v      # Temporal post-processing FSM (k=3 persistence counter)
│   ├── uart_rx.v          # 230,400-baud UART receiver (434 cycles/bit @ 100 MHz)
│   ├── tb_dwt_db4.v       # Cycle-accurate testbench verifying db4 against hex vectors
│   ├── tb_svm_classifier.v# Verification testbench harness for Linear SVM classifier
│   ├── tb_alarm_logic.v   # Testbench harness for persistence FSM and refractory period
│   └── tb_uart_rx.v       # Testbench harness for UART frame synchronization
│
├── vectors/               # Exported bit-exact test vectors for RTL simulation
│   ├── tb_dwt_input.hex           # 512 input samples (signed 16-bit Q1.15)
│   ├── tb_dwt_approx_expected.hex # 256 expected low-pass approximation samples
│   └── tb_dwt_detail_expected.hex # 256 expected high-pass detail samples
│
├── results/               # Ground-truth evaluation CSVs, figures, and models
│   ├── baseline_folds.csv         # 47-record per-fold results for proposed pipeline
│   ├── baseline_metrics.csv       # Per-subject and pooled summary metrics
│   ├── shoeb_folds.csv            # 47-record per-fold results for replicated baseline
│   ├── shoeb_replication.csv      # Replication summary metrics
│   ├── ablation_table.csv         # Comprehensive 14-row ablation table
│   ├── wordlength_study.csv       # SQNR, feature distortion, and accumulator widths
│   ├── seizure_onset_validation.png# 3-panel temporal validation plot (chb01_03.edf)
│   ├── k_tradeoff.png             # Sensitivity vs FA/h trade-off curve
│   ├── wordlength_plot.png        # SQNR and feature error vs word length B
│   └── models/                    # Serialized fold-0 models for FPGA export
│
├── data/                  # Frozen experimental dataset metadata (Rule 9 compliant)
│   ├── manifest.csv               # 47 recordings, channel lists, and seizure annotations
│   ├── chb01-summary.txt          # Clinical annotations for subject chb01
│   ├── chb02-summary.txt          # Clinical annotations for subject chb02
│   └── chb03-summary.txt          # Clinical annotations for subject chb03
│
├── report/                # LaTeX source files for Mid-Term Report
│   ├── mtr-15.tex         # Main report source (CVPR template, line-numbered review)
│   ├── refs.bib           # Complete bibliography with DOIs
│   └── cvpr.sty           # IEEE/CVF formatting style sheet
│
└── scripts/               # Automation, verification, and audit tools
    ├── audit_submission.py        # Automated 40-point submission validator
    ├── package_submission.py      # Rule-9 compliant zip packaging script
    ├── regenerate_fig1_corrected.py# Script generating 3-panel Figure 1
    └── run_shoeb_per_fold.py      # Per-fold Shoeb replication logger
```

---

## 3. Quickstart & Reproduction Guide

### Environment Setup
Requires Python 3.10+ (tested on Python 3.11):
```bash
pip install numpy scipy PyWavelets pyedflib scikit-learn pandas matplotlib
```

### Reproducing Tables & Figures from the Report

| Table / Figure in Report | Generating Command | Output CSV / Image |
| :--- | :--- | :--- |
| **Table 1 & Table 6** (Baseline LORO Performance) | `python src/train.py` | `results/baseline_folds.csv`<br>`results/baseline_metrics.csv` |
| **Table 4** (Shoeb Replication Benchmark) | `python src/shoeb_baseline.py` | `results/shoeb_folds.csv`<br>`results/shoeb_replication.csv` |
| **Table 5 & Fig. 2** (Alarm $k$ Ablation Sweep) | `python src/ablate.py` | `results/ablation_table.csv`<br>`results/k_tradeoff.png` |
| **Table 7 & Fig. 3** (Finite Word-Length Analysis) | `python src/fixedpoint.py` | `results/wordlength_study.csv`<br>`results/wordlength_plot.png` |
| **Fig. 1** (3-Panel Seizure Onset Validation) | `python scripts/regenerate_fig1_corrected.py` | `results/seizure_onset_validation.png` |
| **Submission Package & Integrity Audit** | `python scripts/audit_submission.py` | Terminal verification report (40/40 checks) |

---

## 4. Hardware Simulation & RTL Verification

### Bit-Exact DWT Verification (`rtl/dwt_db4.v`)
The Daubechies-4 analysis filter bank implements the 8-tap low-pass ($h$) and high-pass ($g$) filters with signed 16-bit Q1.15 fixed-point coefficients. It is verified against software golden hex vectors:

Using **Icarus Verilog**:
```bash
iverilog -o sim_dwt rtl/tb_dwt_db4.v rtl/dwt_db4.v
vvp sim_dwt
```
*Expected Result:*
```text
Reading stimulus from vectors/tb_dwt_input.hex...
Reading expected approximation from vectors/tb_dwt_approx_expected.hex...
Reading expected detail from vectors/tb_dwt_detail_expected.hex...
Verification SUCCESS! All 256 approximation and detail samples match golden model bit-exactly.
```

Using **Xilinx Vivado (xsim)**:
```tcl
xvlog rtl/dwt_db4.v rtl/tb_dwt_db4.v
xelab tb_dwt_db4 -s tb_dwt_sim
xsim tb_dwt_sim -R
```

---

## 5. Course Policy & Academic Integrity Compliance

1. **Course Rule 9 (Zero Heavy Data Files):**
   In strict compliance with Course Rule 9, zero raw `.edf` or extracted `.npz` files are included in this repository or the submission archive. All data ingestion is governed by `data/manifest.csv` and downloadable directly from PhysioNet.
2. **AI Tool Usage Disclosure:**
   In accordance with course guidelines, all AI interactions (Anthropic Claude 3.5 Sonnet and Google Antigravity) are disclosed in Table 11 of the report and logged chronologically in `process.md`.
3. **Reproducibility Guarantee:**
   All random seeds are explicitly fixed (`RANDOM_SEED = 42` in `src/config.py`). Results are 100% deterministic and reproducible across platforms.
