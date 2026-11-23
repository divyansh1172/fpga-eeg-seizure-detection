# Experiments: Window Alignment and Hardware-Compatible Retraining

**Project:** 22-Channel FPGA Seizure Detection System  
**Target Hardware:** RealDigital Boolean Board (Spartan-7 XC7S50)  
**Directory:** `experiments/window_alignment/`

---

## Overview

This isolated experiment directory hosts the complete software and verification framework developed to investigate and resolve the fundamental temporal window discrepancy between model training and FPGA deployment:

- **Configuration A (`window_1s`):** 1.0-second non-overlapping window ($W=256, H=256$ samples at $256\text{ Hz}$). Aligns natively with the Spartan-7 RTL datapath (`top_seizure_detector.v` and `feature_accumulator.v`).
- **Configuration B (`window_2s`):** 2.0-second $50\%$ overlapping window ($W=512, H=256$ samples at $256\text{ Hz}$). Reproduces the historical software baseline (`src/train.py`).

---

## Directory Organization

```
experiments/window_alignment/
├── README.md                      # This overview and execution guide
├── repository_analysis.md         # Technical baseline audit of existing codebase
├── IMPLEMENTATION_REPORT.md       # Final architectural and verification report
├── configs/
│   ├── window_1s.yaml             # Configuration A (1.0s window, FPGA-aligned)
│   ├── window_1s.json             # JSON equivalent for zero-dependency parsing
│   ├── window_2s.yaml             # Configuration B (2.0s window, software baseline)
│   └── window_2s.json             # JSON equivalent for zero-dependency parsing
├── code/
│   ├── config_loader.py           # Robust YAML/JSON configuration loader
│   ├── feature_pipeline.py        # Causal filtering, db4 DWT, and 176-feature extraction
│   ├── metrics.py                 # Window-level and event-level clinical metrics
│   ├── evaluation.py              # Temporal alarm persistence (k=3) & refractory blanking
│   ├── experiment_runner.py       # LORO training orchestrator and cross-validation loop
│   ├── fixedpoint_evaluation.py   # Genuine bit-accurate RTL fixed-point evaluation engine
│   ├── model_export.py            # FPGA candidate model exporter (.mem, metadata, vectors)
│   └── validation.py              # Standalone verification tool for candidate model artifacts
├── tests/
│   ├── test_windowing.py          # Window and hop slicing, boundary and label tests
│   ├── test_features.py           # DWT dyadic trees, Energy/Line-Length, 176 dimensions
│   ├── test_loro_split.py         # Zero-leakage LORO partitioning and train-only scaling
│   ├── test_fixedpoint.py         # Q15 arithmetic, 40-bit accumulator, anti-duplication, full pipeline
│   ├── test_model_export.py       # .mem formatting, $readmemh compatibility, test vectors
│   ├── test_rtl_cosim.py          # Icarus Verilog co-simulation test harness (9 edge cases)
│   ├── tb_svm_cosim.v             # Isolated Verilog co-simulation testbench for svm_classifier.v
│   └── run_tests.py               # Single entry-point regression test suite runner (15 tests)
├── handoff/
│   ├── PROMPT_00_ENVIRONMENT_AND_METHODOLOGY.md  # Collaborator Preflight & Setup
│   ├── PROMPT_01_TRAIN_AND_EVALUATE.md           # Collaborator Training & LORO
│   ├── PROMPT_02_FIXED_POINT_AND_FPGA_EXPORT.md  # Collaborator Fixed-Point & Export
│   └── PROMPT_03_FINAL_RESULTS_AND_HANDOFF.md    # Collaborator Reporting & Delivery
├── artifacts/
│   ├── README.md                  # Model storage policy and safety rules
│   └── candidate_models/          # Candidate model packages (weights.mem, bias.mem, etc.)
└── reports/
    └── README.md                  # Generated fold CSVs, summaries, and comparison logs
```

---

## Verification & Implementation Status

To maintain scientific integrity, the exact status of each engineering milestone is explicitly distinguished below:

| Verification Milestone | Status | Details & Evidence |
| :--- | :--- | :--- |
| **Framework Implementation** | **COMPLETE** | Isolated modular architecture with dual YAML/JSON configs, zero external dependencies beyond NumPy/SciPy. |
| **Synthetic Infrastructure Testing** | **COMPLETE** | 15 / 15 unit tests passing 100% green via `run_tests.py`. |
| **SVM RTL Co-Simulation** | **COMPLETE** | Bit-exact verification against `rtl/svm_classifier.v` via Icarus Verilog across 9 deterministic edge cases. |
| **Fixed-Point Pipeline Emulation** | **COMPLETE** | Added `FixedChannelIIR`, `FixedChannelDWT`, and `run_bit_exact_fpga_pipeline()` in `fixedpoint_evaluation.py`. |
| **Full-Dataset Retraining** | **PENDING** | To be executed by collaborator via `handoff/PROMPT_01_TRAIN_AND_EVALUATE.md`. |
| **Clinical Metrics on Cohort** | **PENDING** | Event sensitivity and FA/h across 47 CHB-MIT recordings pending collaborator training run. |
| **Bit-Exact Hardware Verification on Live Data** | **PENDING** | Full end-to-end dataset evaluation with fixed-point pipeline pending collaborator execution of `PROMPT_02`. |
| **Physical Spartan-7 Board Validation** | **PENDING** | Bitstream programming and real-time UART testing on physical Boolean Board pending Phase 3. |

---

## Quickstart: Running Infrastructure Tests

To verify that all experiment infrastructure modules are functioning correctly with 100% green tests (including Verilog co-simulation):

```bash
python3 experiments/window_alignment/tests/run_tests.py
```
