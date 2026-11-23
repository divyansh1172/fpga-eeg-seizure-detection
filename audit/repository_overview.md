# Technical Audit: Repository Overview & Manifest
**Project:** FPGA-Based Real-Time Multichannel EEG Seizure Detection  
**Target Hardware:** RealDigital Boolean Board (AMD Spartan-7 `xc7s50csga324-1`)  
**Clock Domain:** 100.000 MHz Onboard MEMS Oscillator (10.0 ns period)  
**Academic Context:** Course EE2000 (Signal Processing), Fall 2026, Indian Institute of Technology Hyderabad (Team 15)  
**Audit Date:** November 2026  

---

## 1. Project Purpose & High-Level Scope

This repository houses a complete hardware-software co-design implementation for automated, patient-specific epileptic seizure detection from continuous 22-channel scalp electroencephalogram (EEG) recordings. The clinical baseline is drawn from the PhysioNet CHB-MIT Scalp EEG Database.

The operational pipeline is partitioned into two major domains:
1. **Algorithmic Software Exploration (`src/`, `golden/`, `tools/`):**
   - End-to-end data ingestion, causal bandpass preprocessing (0.5–25 Hz), 5-level Daubechies-4 (db4) Discrete Wavelet Transform (DWT), feature extraction (Sub-band Energy and Line-Length), and patient-specific Leave-One-Record-Out (LORO) Linear Support Vector Machine (SVM) training.
   - Offline parameter folding that converts floating-point standardization ($\mu, \sigma$) and classification hyperplanes ($w, b$) into hardware-amenable integer weights and bias.
   - Bit-accurate integer and floating-point golden reference modeling (`golden/golden.py`).
2. **Synthesizable FPGA RTL Datapath (`rtl/`):**
   - Time-multiplexed, 22-channel hardware datapath targeting an AMD Spartan-7 XC7S50 FPGA on the RealDigital Boolean Board.
   - Subsystem cascade: 230,400-baud UART Packet Receiver $\to$ 22-channel Direct Form I IIR Biquad Filter $\to$ 5-level Dyadic db4 DWT Cascade $\to$ Double-Buffered Ping-Pong Feature Accumulators $\to$ 176-cycle Serial Linear SVM MAC Classifier $\to$ Persistence & Refractory Alarm FSM $\to$ Dual 4-Digit 7-Segment Display, Board LEDs, and Telemetry UART Transmitter.

---

## 2. Directory Layout & File Manifest

The repository root is organized as follows:

```text
fpga-eeg-seizure-detection/
├── rtl/                        # Synthesizable Verilog sources, testbenches, constraints, ROMs
│   ├── top_seizure_detector.v  # Top-level integration wrapper & board I/O mapping
│   ├── uart_rx.v               # 230,400-baud UART receiver with framing error detection
│   ├── uart_tx.v               # 230,400-baud UART telemetry transmitter (sends 0xA5 alert)
│   ├── iir_biquad.v            # 22-ch time-multiplexed 4th-order Butterworth bandpass (0.5-25 Hz)
│   ├── dwt_level.v             # Modular single-level db4 FIR decomposition with per-ch state
│   ├── dwt_db4.v               # 5-level dyadic cascade emitting D3, D4, D5, A5 subbands
│   ├── feature_accumulator.v   # Ping-pong double-buffered Energy & Line-Length accumulator
│   ├── svm_classifier.v        # 176-cycle serial MAC with 40-bit accumulator & 32-bit bias
│   ├── alarm_logic.v           # k-consecutive persistence (k in {1,2,3,5}) & 30s refractory blanking
│   ├── seven_seg_controller.v  # Dual 4-digit common-anode 7-segment display driver
│   ├── boolean_board.xdc       # Physical pin & timing constraints for Spartan-7 XC7S50
│   ├── weights.mem             # Hex initialization file (176 x 16-bit signed folded weights)
│   ├── bias.mem                # Hex initialization file (1 x 32-bit signed folded bias)
│   ├── tb_top_seizure_detector.v # Top-level system integration testbench
│   ├── tb_uart_rx.v            # UART RX frame synchronization and error recovery testbench
│   ├── tb_iir_biquad.v         # 22-channel IIR filter testbench against golden vectors
│   ├── tb_dwt_db4.v            # 5-level DWT testbench against golden vectors
│   ├── tb_feature_accumulator.v# Feature accumulator and boundary race testbench
│   ├── tb_svm_classifier.v     # 60-window SVM inference bit-exact testbench
│   ├── tb_alarm_logic.v        # Persistence, refractory blanking, and clear testbench
│   └── tb_seven_seg_controller.v # Display controller simulation testbench
│
├── src/                        # Python software pipeline & scientific evaluation suite
│   ├── config.py               # Central frozen configuration, hyperparams, and montage paths
│   ├── data_io.py              # PhysioNet CHB-MIT EDF file reader and annotation parser
│   ├── preprocess.py           # 22-channel extraction, windowing, and label assignment
│   ├── dwt.py                  # PyWavelets reference DWT and causal streaming FIR DWT
│   ├── features.py             # Sub-band Energy (E) and Line-Length (LL) extractor
│   ├── train.py                # Patient-specific Leave-One-Record-Out (LORO) SVM trainer
│   ├── postprocess.py          # Temporal k-consecutive window persistence filter
│   ├── evaluate.py             # Event-level clinical scoring (Sensitivity, FA/h, Latency)
│   ├── shoeb_baseline.py       # Independent replication of Shoeb & Guttag (ICML 2010)
│   ├── ablate.py               # 4D ablation sweeps (k, features, bands, regularization C)
│   └── fixedpoint.py           # Word-length study (B in 8..16 bits) and SQNR characterization
│
├── golden/                     # Bit-accurate mathematical reference model & test vectors
│   ├── golden.py               # Comprehensive 64-bit float and integer fixed-point model
│   ├── README.md               # Golden model architecture documentation and execution guide
│   ├── w_eff_chb01.npy         # Serialized folded effective weights (numpy)
│   ├── b_eff_chb01.npy         # Serialized folded effective bias (numpy)
│   └── vectors/                # 12 pre-generated .hex / .mem test vectors for RTL verification
│       ├── tb_uart_rx_stimulus.hex    # 45,056 bytes of framed 22-ch UART stimulus
│       ├── tb_iir_input.hex           # 11,264 raw interleaved input samples
│       ├── tb_iir_expected.hex        # 11,264 expected bandpass-filtered samples
│       ├── tb_dwt_input.hex           # DWT input stimulus
│       ├── tb_dwt_d3_expected.hex     # Subband D3 expected coefficients
│       ├── tb_dwt_d4_expected.hex     # Subband D4 expected coefficients
│       ├── tb_dwt_d5_expected.hex     # Subband D5 expected coefficients
│       ├── tb_dwt_a5_expected.hex     # Subband A5 expected coefficients
│       ├── tb_features_expected.hex   # 10,560 expected normalized features (60 windows)
│       ├── weights.mem                # 176 signed 16-bit SVM weights
│       ├── bias.mem                   # 1 signed 32-bit SVM bias
│       ├── tb_svm_scores_expected.hex # 60 expected 40-bit SVM dot-product scores
│       ├── tb_decisions_expected.hex  # 60 expected binary decisions
│       └── tb_alarms_expected.hex     # 60 expected post-processed alarm states
│
├── tools/
│   └── export_svm.py           # Offline weight/bias folding and .mem export script
│
├── scripts/                    # Automation, execution, and verification utilities
│   ├── run_vivado_synth.tcl    # Automated non-project batch synthesis & implementation script
│   ├── stream_eeg_uart.py      # Host Python UART streaming harness (230,400 baud)
│   ├── run_all.sh              # Bash regression harness running 7 Icarus Verilog testbenches
│   ├── run_s1.py               # Step S1 rule evaluation & manifest generation runner
│   ├── run_shoeb_per_fold.py   # Fold-level Shoeb replication logger
│   ├── run_fixedpoint_loro.py  # Stage 8 full-cohort fixed-point LORO evaluation script
│   ├── generate_3panel_validation.py # Generates 3-panel seizure validation figure
│   ├── regenerate_fig1_corrected.py # Generates corrected Figure 1 for final report
│   ├── download_data.py        # Automated CHB-MIT record downloader
│   ├── overnight_pipeline.py   # Full automated execution of Stages 1 through 5
│   ├── package_submission.py   # Mid-term packaging script (Rule 9 compliant)
│   ├── package_final_submission.py # Final submission packaging script
│   ├── audit_submission.py     # Mid-term 40-point automated audit validator
│   ├── audit_final_submission.py # Final submission pre-flight audit validator
│   ├── verify_numbers.py       # Consistency auditor checking CSV metrics against text
│   ├── apply_audit3_clean.py   # LaTeX report cleanup utility
│   ├── apply_audit4_clean.py   # LaTeX report cleanup utility
│   └── apply_review_fixes.py   # Minor document patch script
│
├── data/                       # Experimental metadata & clinical annotations (Zero raw EDF/NPZ)
│   ├── manifest.csv            # 47 recording entries across chb01, chb02, chb03 with seizure intervals
│   ├── chb01-summary.txt       # Clinical annotation summary for subject chb01
│   ├── chb02-summary.txt       # Clinical annotation summary for subject chb02
│   ├── chb03-summary.txt       # Clinical annotation summary for subject chb03
│   ├── raw/                    # Intentionally empty / excluded per Rule 9
│   └── processed/              # Intentionally empty / excluded per Rule 9
│
├── results/                    # Ground-truth evaluation CSVs, figures, and serialized models
│   ├── baseline_metrics.csv    # Subject-level pooled metrics (Sensitivity, FA/h, Latency)
│   ├── baseline_folds.csv      # 47-record per-fold metrics for proposed DWT + Linear SVM
│   ├── shoeb_replication.csv   # Subject-level replicated Shoeb (2010) metrics
│   ├── shoeb_folds.csv         # 47-record per-fold replicated Shoeb metrics
│   ├── ablation_table.csv      # 14-row ablation study (k, feature subsets, subbands, C)
│   ├── wordlength_study.csv    # SQNR, feature distortion, and accumulator widths vs word length
│   ├── fixedpoint_loro_comparison.csv # Float vs. Fixed-Point LORO comparison table
│   ├── uart_demo_playback.log  # Hardware UART streaming execution log
│   ├── seizure_onset_validation.png # 3-panel temporal validation plot (chb01_03.edf)
│   ├── k_tradeoff.png          # Sensitivity vs. False Alarm Rate trade-off curve
│   ├── wordlength_plot.png     # SQNR and feature distortion vs. Word Length B
│   └── models/                 # Serialized scikit-learn models (chb01, chb02, chb03 fold-0)
│
├── endsem report/              # Complete Endsem execution guidelines, checklists, and prompts
│   ├── README.md               # Endsem phase roadmap and milestones
│   ├── recquirement.txt        # Detailed technical and teammate requirements
│   ├── MASTER_CONTEXT.md       # 360-degree mathematical, signal processing, and hardware context
│   ├── AGENT_PROMPT.md         # Master turnkey prompt for coding agents
│   ├── CHECKLIST.md            # Definition of Done and pre-submission audit checklist
│   ├── TEAM_WORK_DELINEATION.md# Breakdown of member contributions (M1-M4)
│   ├── VIVA_DEFENSE_GUIDE.md   # Comprehensive technical Q&A preparation for oral defense
│   ├── PART1_RTL_COMPLETION.md # Task guide: RTL datapath completion and integration
│   ├── PART2_VIVADO_SYNTHESIS.md # Task guide: Batch Vivado synthesis and timing closure
│   ├── PART3_HARDWARE_DEMO.md  # Task guide: Physical Boolean Board demo and UART streaming
│   ├── PART4_QUANTIZATION_LORO.md # Task guide: Full-cohort fixed-point LORO re-evaluation
│   └── PART5_FINAL_REPORT_VIVA.md # Task guide: Final report authorship and packaging
│
├── report/                     # LaTeX source files for milestone reports
│   ├── final-15.tex            # Main IEEE/CVF two-column LaTeX final project report
│   ├── mtr-15.tex              # Mid-term milestone LaTeX report
│   ├── refs.bib / references.bib # Comprehensive BibTeX references with DOIs
│   └── cvpr.sty                # IEEE/CVF LaTeX style sheet
│
├── fpr-15/                     # Packaged submission staging directory (mirror of deliverables)
├── fpr-15.zip                  # Packaged submission archive (2.8 MB, Rule 9 compliant)
├── final-15.pdf                # Compiled final project report (6-page IEEE review format)
├── mtr-15.pdf                  # Compiled mid-term project report
├── ANTIGRAVITY_FIX_PLAN.md     # Detailed line-by-line audit and fix plan for initial scaffolding bugs
├── CHANGELOG.md                # Execution ledger documenting bug fixes across Phases 0–3
└── process.md                  # Append-only engineering log and AI interaction ledger
```

---

## 3. Directory Duplication & Asset Relationships

A key structural finding of this audit is the existence of multiple redundant directories and duplicate files:
1. **`fpr-15/` and `fpr-15.zip`:**
   - `fpr-15/` is an exact duplicate packaging branch of the root deliverables (`rtl/`, `src/`, `results/`, `scripts/`, `data/`, `endsem report/`, `final-15.pdf`).
   - `fpr-15.zip` is the submitted release archive corresponding to `fpr-15/`.
2. **`endsem report/` vs. `fpr-15/endsem report/`:**
   - Both contain identical execution prompts, task descriptions, and checklists.
3. **Memory Initialization Files (`weights.mem` / `bias.mem`):**
   - Present simultaneously in:
     - Root directory: `./weights.mem`, `./bias.mem`
     - RTL directory: `rtl/weights.mem`, `rtl/bias.mem`
     - Golden vectors directory: `golden/vectors/weights.mem`, `golden/vectors/bias.mem`
     - Packaged staging: `fpr-15/rtl/weights.mem`, `fpr-15/rtl/bias.mem`
   - *Confirmed fact:* `top_seizure_detector.v` invokes `$readmemh("weights.mem", svm_weight_rom)` at line 318, requiring `weights.mem` to reside in the working directory from which Vivado or Icarus Verilog is launched.
4. **Test Stimulus Vectors (`vectors/` vs. `golden/vectors/`):**
   - `vectors/` contains legacy 512-sample test vectors (`tb_dwt_input.hex`, `tb_dwt_approx_expected.hex`, `tb_dwt_detail_expected.hex`).
   - `golden/vectors/` contains the full 12-file suite of multi-channel, 1.0-second window test vectors generated by `golden/golden.py`.

---

## 4. Build Environment, Dependencies & Toolchains

The repository is designed to build and verify across two distinct toolchains:

### A. RTL Hardware Simulation & Synthesis
| Tool | Version Target | Invocation Script | Purpose |
|---|---|---|---|
| **Icarus Verilog** (`iverilog`) | 12.0+ (Verilog-2001) | `./run_all.sh` | Compiles and executes 7 self-checking testbenches with `-Wall` |
| **VVP Runtime Engine** (`vvp`) | 12.0+ | `vvp sim_<module>` | Executes compiled simulation binaries and emits logs |
| **AMD Xilinx Vivado** | 2020.2 or later | `scripts/run_vivado_synth.tcl` | Non-project batch synthesis, placement, routing, and bitstream generation for `xc7s50csga324-1` |

### B. Software Pipeline & Data Processing
* **Python Runtime:** Python 3.10+ (tested under Python 3.11 / 3.12 / 3.15 virtual environments).
* **Core Libraries:**
  - `numpy` ($\ge 1.22$): High-performance vector arithmetic, Q15 fixed-point emulation.
  - `scipy` ($\ge 1.8$): Digital filter design (`scipy.signal.butter`, `scipy.signal.sosfilt`).
  - `pywt` (`PyWavelets` $\ge 1.3$): Daubechies-4 discrete wavelet transform reference.
  - `scikit-learn` ($\ge 1.0$): `LinearSVC` classification, `StandardScaler`.
  - `pandas` ($\ge 1.4$): Tabular evaluation, metrics aggregation, manifest handling.
  - `pyserial` ($\ge 3.5$): USB-UART host communication for physical board streaming demo.
  - `matplotlib` ($\ge 3.5$): Validation figures, trade-off curves, waveform plots.

---

## 5. Frozen Dataset Protocols & Hyperparameters

Per project documentation and `src/config.py`:
* **Dataset:** PhysioNet CHB-MIT Scalp EEG Database.
* **Subjects:** `chb01`, `chb02`, `chb03` (47 recordings totaling 45.63 non-seizure hours and 17 clinical seizures).
* **Sampling Rate:** $f_s = 256$ Hz ($T_s \approx 3.906$ ms).
* **Electrode Montage:** Standard 22 unique bipolar channels:
  `FP1-F7`, `F7-T7`, `T7-P7`, `P7-O1`, `FP1-F3`, `F3-C3`, `C3-P3`, `P3-O1`, `FP2-F4`, `F4-C4`, `C4-P4`, `P4-O2`, `FP2-F8`, `F8-T8`, `T8-P8`, `P8-O2`, `FZ-CZ`, `CZ-PZ`, `P7-T7`, `T7-FT9`, `FT9-FT10`, `FT10-T8`.
* **Subbands:** 4 retained dyadic subbands: D3 (16–32 Hz), D4 (8–16 Hz), D5 (4–8 Hz), A5 (0–4 Hz).
* **Features per Subband:** Energy ($E$) and Line-Length ($LL$) $\implies 22 \times 4 \times 2 = 176$ features.
* **Classifier:** Linear SVM with balanced class weighting, $C = 1.0$.
* **Alarm Filter:** $k$-consecutive window persistence ($k=3$ default baseline), 30-second refractory blanking, 2.0-second clinical detection tolerance window.
