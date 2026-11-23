# Graph Report - fpga-eeg-seizure-detection  (2026-11-23)

## Corpus Check
- 168 files · ~136,590 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 122 file(s) not represented in the graph (top: .hex 19, .csv 18, .tex 13)
- WARNING: 122 of 290 files seen (42%) have no supported extractor and are missing from this graph entirely. It may look complete while representing only part of the codebase.

## Summary
- 821 nodes · 1658 edges · 102 communities (47 shown, 55 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 303 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Submission Audit & Verification
- Architecture Changelog & Roadmap
- Shoeb Replication & Evaluation
- Golden Reference Model
- Fixed-Point Quantization & LORO
- Seizure Validation & Visualizations
- Seizure Validation & Visualizations
- RTL Testbenches & Alarm Logic
- Seizure Validation & Visualizations
- Fixed-Point Quantization & LORO
- Submission Audit & Verification
- Wavelet Decomposition (DWT)
- Viva Defense & Technical Q&A
- Linear SVM Export & Inference
- Wavelet Decomposition (DWT)
- Submission Audit & Verification
- Wavelet Decomposition (DWT)
- CHB-MIT Patient Records
- Project Documentation & Reports
- RTL Testbenches & Alarm Logic
- Wavelet Decomposition (DWT)
- Plan Seizure
- Seizure Validation & Visualizations
- Wavelet Decomposition (DWT)
- FPGA RTL Architecture
- Viva Defense & Technical Q&A
- EEG Preprocessing & Filtering
- FPGA RTL Architecture
- Wavelet Decomposition (DWT)
- Seizure Validation & Visualizations
- Wavelet Decomposition (DWT)
- FPGA RTL Architecture
- Viva Defense & Technical Q&A
- EEG Preprocessing & Filtering
- Project Documentation & Reports
- Wavelet Decomposition (DWT)
- Golden Reference Model
- Wavelet Decomposition (DWT)
- Project Documentation & Reports
- Subject Selection & Rules (S1)
- Wavelet Decomposition (DWT)
- Linear SVM Export & Inference
- Viva Defense & Technical Q&A
- RTL Testbenches & Alarm Logic
- Viva Defense & Technical Q&A
- Feature Extraction
- Wavelet Decomposition (DWT)
- Refractory Alarms
- Wavelet Decomposition (DWT)
- Wavelet Decomposition (DWT)
- Wavelet Decomposition (DWT)
- Feature Extraction
- Seven Seg
- Alarm Consecutive
- Shoeb Replication & Evaluation
- Feature Extraction
- Seven Seg
- Run All
- Shoeb Replication & Evaluation
- RTL Testbenches & Alarm Logic
- EEG Preprocessing & Filtering
- Linear SVM Export & Inference
- RTL Testbenches & Alarm Logic
- RTL Testbenches & Alarm Logic
- Uart
- Uart
- RTL Testbenches & Alarm Logic
- EEG Preprocessing & Filtering
- Linear SVM Export & Inference
- RTL Testbenches & Alarm Logic
- RTL Testbenches & Alarm Logic
- RTL Testbenches & Alarm Logic
- RTL Testbenches & Alarm Logic
- Uart
- Uart

## God Nodes (most connected - your core abstractions)
1. `RealDigital Boolean Board` - 36 edges
2. `UART EEG Streaming Interface` - 36 edges
3. `Discrete Wavelet Transform (DWT)` - 34 edges
4. `Linear Support Vector Machine` - 32 edges
5. `Vivado Synthesis & Implementation` - 29 edges
6. `Xilinx Spartan-7 XC7S50 FPGA` - 27 edges
7. `run_loro_training_for_subject()` - 22 edges
8. `audit_final_submission()` - 20 edges
9. `CHB-MIT Scalp EEG Database` - 20 edges
10. `Leave-One-Record-Out (LORO) CV` - 20 edges

## Surprising Connections (you probably didn't know these)
- `EE2000 Signal Processing — Boolean Board Project Research Report` --references--> `tb_alarm_logic`  [INFERRED]
  part1.md → fpr-15/rtl/tb_alarm_logic.v
- `Top-Tier EE2000 Signal Processing Projects` --references--> `tb_alarm_logic`  [INFERRED]
  Top_Tier_Boolean_Board_Projects.md → fpr-15/rtl/tb_alarm_logic.v
- `EE2000 Seizure Detector – Antigravity Fix Plan` --references--> `stream_hex_vector()`  [INFERRED]
  ANTIGRAVITY_FIX_PLAN.md → fpr-15/scripts/stream_eeg_uart.py
- `PART 1: RTL Completion & Top-Level Integration (Stage 6A)` --references--> `stream_hex_vector()`  [INFERRED]
  endsem report/PART1_RTL_COMPLETION.md → fpr-15/scripts/stream_eeg_uart.py
- `RealDigital Boolean Board (AMD Spartan-7 XC7S50)` --references--> `stream_hex_vector()`  [INFERRED]
  FPGA_UPLOAD_TUTORIAL.md → fpr-15/scripts/stream_eeg_uart.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Module Context Group 1** — agent_prompt, agent_prompt_your_role, agent_prompt_project_in_6_lines_so_you_neve, agent_prompt_non_negotiable_rules [INFERRED 0.75]
- **Module Context Group 2** — endsem_report_part5_final_report_viva, endsem_report_part5_final_report_viva_compliance_with_the_ee2000_fin, endsem_report_part5_final_report_viva_key_upgrades_from_mid_term_mtr, endsem_report_part5_final_report_viva_team_member_work_delineation_t [INFERRED 0.75]
- **Module Context Group 3** — mid_term_report_agent_prompt, mid_term_report_agent_prompt_your_role, mid_term_report_agent_prompt_project_in_6_lines_so_you_neve, mid_term_report_agent_prompt_non_negotiable_rules [INFERRED 0.75]
- **Module Context Group 4** — fpr_15_results_wordlength_plot, mtr_page1, page1, page2 [INFERRED 0.75]

## Communities (102 total, 55 thin omitted)

### Community 0 - "Submission Audit & Verification"
Cohesion: 0.05
Nodes (22): audit_final_submission(), audit(), download_file(), main(), safe_replace(), package(), should_include(), package() (+14 more)

### Community 1 - "Architecture Changelog & Roadmap"
Cohesion: 0.06
Nodes (30): EE2000 Seizure Detector – Execution Changelog, Phase 0: Architecture & Issue Confirmation, Phase 1: Golden Reference Model (`golden/golden.py`), Phase 2, Task 4: Feature Accumulator & Ping-Pong Buffering (S3, S4, S5, M8, C3), Phase 2, Task 5: Linear SVM Classifier & Real Model Weights (C7), Phase 2, Task 6: Alarm Logic, Telemetry & Display Behavior (C5, C6, M3, M6, M7), Phase 2, Task 7: Reset Synchronizer, Lint & RTL Cleanup (M2, M9), Phase 3: Full-System Integration & Automated Regression Suite (+22 more)

### Community 2 - "Shoeb Replication & Evaluation"
Cohesion: 0.09
Nodes (14): generate_replication_comparison_table(), main(), run_shoeb_replication_for_subject(), load_record_data(), main(), run_loro_training_for_subject(), aggregate_subject_metrics(), merge_refractory_alarms() (+6 more)

### Community 3 - "Golden Reference Model"
Cohesion: 0.07
Nodes (15): compute_hardware_scales(), compute_sqnr(), Dummy, dump_test_vectors(), FixedChannelDWT, FixedChannelIIR, FloatChannelDWT, FloatChannelIIR (+7 more)

### Community 4 - "Fixed-Point Quantization & LORO"
Cohesion: 0.11
Nodes (15): aggregate_subject_metrics(), compute_sqnr(), export_hex_test_vectors(), fixed_point_dwt_1level(), main(), quantize_to_b_bits(), run_wordlength_sweep(), streaming_dwt_1level() (+7 more)

### Community 5 - "Seizure Validation & Visualizations"
Cohesion: 0.15
Nodes (9): main(), main(), main(), main(), apply_causal_bandpass(), create_causal_bandpass_filter(), extract_record_features(), extract_subband_features() (+1 more)

### Community 6 - "Seizure Validation & Visualizations"
Cohesion: 0.12
Nodes (11): main(), main(), build_manifest(), download_summary_file(), evaluate_subject_rules(), parse_summary_file(), read_edf(), compute_window_labels() (+3 more)

### Community 7 - "RTL Testbenches & Alarm Logic"
Cohesion: 0.11
Nodes (8): tb_dwt_db4, tb_iir_biquad, tb_seven_seg_controller, tb_svm_classifier, top_seizure_detector, tb_dwt_db4, tb_svm_classifier, top_seizure_detector

### Community 8 - "Seizure Validation & Visualizations"
Cohesion: 0.14
Nodes (11): main(), run_c_ablation(), run_feature_ablation(), run_k_ablation(), run_subband_ablation(), main(), run_c_ablation(), run_feature_ablation() (+3 more)

### Community 9 - "Fixed-Point Quantization & LORO"
Cohesion: 0.14
Nodes (7): run_fixedpoint_loro_evaluation(), compute_window_labels(), generate_sanity_plot(), main(), process_record(), run_fixedpoint_loro_evaluation(), main()

### Community 10 - "Submission Audit & Verification"
Cohesion: 0.17
Nodes (12): RealDigital Boolean Board, Q1.15 Fixed-Point Quantization, Vivado Synthesis & Implementation, PART 5: Final Report Authorship, Packaging & Viva Readiness (Stage 9), Compliance with the EE2000 Final Project Rubric, Key Upgrades from Mid-Term (`mtr-15`) to Final Report (`final-15`), Packaging and Pre-Submission Audit, PROMPT TO EXECUTE PART 5: (+4 more)

### Community 11 - "Wavelet Decomposition (DWT)"
Cohesion: 0.19
Nodes (6): apply_causal_bandpass(), compute_dwt_stage_a(), compute_dwt_stage_b(), create_causal_bandpass_filter(), cross_check_stages(), streaming_dwt_1level()

### Community 12 - "Viva Defense & Technical Q&A"
Cohesion: 0.17
Nodes (13): Leave-One-Record-Out (LORO) CV, Xilinx Spartan-7 XC7S50 FPGA, EE2000 Final Project: Endsem Phase Execution Guide, Directory Layout & Document Map, Executive Roadmap & Objectives, Key Milestones & Dates, Quick-Start Guide for Teammates, EE2000 Final Project: Team Work Delineation & Code Ownership (+5 more)

### Community 13 - "Linear SVM Export & Inference"
Cohesion: 0.22
Nodes (6): compute_scales(), Dummy, export_weights(), load_svm_model(), main(), SafeUnpickler

### Community 14 - "Wavelet Decomposition (DWT)"
Cohesion: 0.20
Nodes (10): CHB-MIT Scalp EEG Database, UART EEG Streaming Interface, EE2000 Final Project: Viva Defense Battlecard & Technical Q&A, Q1: Why did you choose DWT + Linear SVM instead of a modern Deep Learning model (e.g., 1D-CNN or Transformer)?, Q2: A Xilinx DSP48E1 multiplier port is $25 \times 18$ bits. Table 7 shows your raw Energy accumulator is 38 bits wide. How can you feed it into the DSP48E1 slice in a single clock cycle without cascading slices?, Q3: In Section 5.2, you mention an impulse-response memory span of 218 samples ($0.85\text{ s}$) but claim a group delay of only $\approx 0.25\text{ s}$. Why the difference?, Q4: Channels 3 (`T7-P7`) and 19 (`P7-T7`) in CHB-MIT have inverted electrode polarities ($y = -x$). How does your pipeline handle this?, Q5: How does offline weight folding save FPGA resources and latency? (+2 more)

### Community 15 - "Submission Audit & Verification"
Cohesion: 0.17
Nodes (9): 1. COURSE REQUIREMENTS, DATASET, DWT, IMPORTANT: LATEX FORMAT, Preprocessing, PROJECT BACKGROUND, SIGNAL-PROCESSING APPROACH, Windowing (+1 more)

### Community 16 - "Wavelet Decomposition (DWT)"
Cohesion: 0.27
Nodes (3): compute_dwt_stage_a(), compute_dwt_stage_b(), cross_check_stages()

### Community 18 - "Project Documentation & Reports"
Cohesion: 0.22
Nodes (9): Linear Support Vector Machine, PART 4: Full-Cohort Fixed-Point Quantization LORO (Stage 8), Context & Motivation, Execution & Verification Flow, Expected Results & Consistency Check, Fixed-Point Arithmetic Model, From project root:, LaTeX Comparison Table for Final Report: (+1 more)

### Community 19 - "RTL Testbenches & Alarm Logic"
Cohesion: 0.25
Nodes (5): tb_alarm_logic, send_decision, tb_alarm_logic, send_decision, tick_second

### Community 20 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): AGENT PROMPT: EE2000 EEG Seizure Detection (DWT + linear SVM) - Mid-term execution, Decisions log, Non-negotiable rules, process.md - EE2000 EEG seizure detection work log, process.md protocol (the user reads this to know what was done), Project in 6 lines (so you never lose the thread), Status board, Your role

### Community 21 - "Plan Seizure"
Cohesion: 0.25
Nodes (8): EE2000 Seizure Detector – Antigravity Fix Plan, Critical, Fixed system facts, Global rules (apply to every task), Known issues (source of truth for this plan), Minor, Phase 0: Confirm understanding (no code), Serious

### Community 22 - "Seizure Validation & Visualizations"
Cohesion: 0.25
Nodes (8): AGENT PROMPT: EE2000 EEG Seizure Detection on FPGA — Endsem Phase Execution, Endsem Step-by-Step Execution Plan, Non-Negotiable Rules, Step S6A: Complete Verilog RTL Datapath (Modules & Testbenches), Step S6B: Vivado Synthesis, Place & Route, and Timing Closure, Step S7: Physical Boolean Board Playback Demo, Step S8: Full-Cohort Quantized Fixed-Point LORO Validation, Your Role & Mission

### Community 23 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): EE2000 Final Project: Master Technical Context & Architecture, Causal Bandpass Preprocessing, Dataset & Signal Processing Protocol, Hardware Dynamic-Range Wire-Shift, -Level Dyadic Daubechies-4 (db4) DWT, Mathematical Foundations & Hardware Optimizations, Offline Weight Folding (Zero DSP Divider / Scaler), System High-Level Architecture

### Community 24 - "FPGA RTL Architecture"
Cohesion: 0.25
Nodes (8): PART 1: RTL Completion & Top-Level Integration (Stage 6A), Boolean Board 7-Segment Controller (`rtl/seven_seg_controller.v`), Context & Architecture Status, Feature Accumulators with Wire-Shift (`rtl/feature_accumulator.v`), Front-End Causal IIR Bandpass (`rtl/iir_biquad.v`), Technical Specifications for Each Module, Top-Level System Wrapper (`rtl/top_seizure_detector.v`), Turnkey Execution Prompt for Part 1

### Community 25 - "Viva Defense & Technical Q&A"
Cohesion: 0.25
Nodes (8): PART 2: Vivado Synthesis, Implementation & Timing Closure (Stage 6B), Context & Objectives, From the project root:, Generated Output Files in `results/`, How to Run Batch Synthesis, Non-Project Batch Tcl Synthesis Flow, Physical Pin Constraints (`rtl/boolean_board.xdc`), Resource & Timing Verification Checklist

### Community 26 - "EEG Preprocessing & Filtering"
Cohesion: 0.25
Nodes (8): PART 3: Real-Time Hardware Playback Demonstration (Stage 7), From project root:, Hardware Setup & Connection, Host Streaming Harness (`scripts/stream_eeg_uart.py`), Latency Verification & Filter Group Delay Characterization, Physical Board Indicators During Demonstration, Running the Streaming Demo:, UART Binary Streaming Protocol

### Community 27 - "FPGA RTL Architecture"
Cohesion: 0.25
Nodes (8): RealDigital Boolean Board (AMD Spartan-7 XC7S50), Complete Step-by-Step FPGA Implementation & Live Demo Tutorial, Hardware:, Hardware Setup & Controls Configuration, Method A: Automated Batch Command (Recommended & Fast), Prerequisites & Equipment Checklist, Software & Repository Files:, Step 1: Generate the FPGA Bitstream

### Community 28 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): AGENT PROMPT: EE2000 EEG Seizure Detection (DWT + linear SVM) - Mid-term execution, Decisions log, Non-negotiable rules, process.md - EE2000 EEG seizure detection work log, process.md protocol (the user reads this to know what was done), Project in 6 lines (so you never lose the thread), Status board, Your role

### Community 29 - "Seizure Validation & Visualizations"
Cohesion: 0.25
Nodes (8): AGENT PROMPT: EE2000 EEG Seizure Detection on FPGA — Endsem Phase Execution, Endsem Step-by-Step Execution Plan, Non-Negotiable Rules, Step S6A: Complete Verilog RTL Datapath (Modules & Testbenches), Step S6B: Vivado Synthesis, Place & Route, and Timing Closure, Step S7: Physical Boolean Board Playback Demo, Step S8: Full-Cohort Quantized Fixed-Point LORO Validation, Your Role & Mission

### Community 30 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): EE2000 Final Project: Master Technical Context & Architecture, Causal Bandpass Preprocessing, Dataset & Signal Processing Protocol, Hardware Dynamic-Range Wire-Shift, -Level Dyadic Daubechies-4 (db4) DWT, Mathematical Foundations & Hardware Optimizations, Offline Weight Folding (Zero DSP Divider / Scaler), System High-Level Architecture

### Community 31 - "FPGA RTL Architecture"
Cohesion: 0.25
Nodes (8): PART 1: RTL Completion & Top-Level Integration (Stage 6A), Boolean Board 7-Segment Controller (`rtl/seven_seg_controller.v`), Context & Architecture Status, Feature Accumulators with Wire-Shift (`rtl/feature_accumulator.v`), Front-End Causal IIR Bandpass (`rtl/iir_biquad.v`), Technical Specifications for Each Module, Top-Level System Wrapper (`rtl/top_seizure_detector.v`), Turnkey Execution Prompt for Part 1

### Community 32 - "Viva Defense & Technical Q&A"
Cohesion: 0.25
Nodes (8): PART 2: Vivado Synthesis, Implementation & Timing Closure (Stage 6B), Context & Objectives, From the project root:, Generated Output Files in `results/`, How to Run Batch Synthesis, Non-Project Batch Tcl Synthesis Flow, Physical Pin Constraints (`rtl/boolean_board.xdc`), Resource & Timing Verification Checklist

### Community 33 - "EEG Preprocessing & Filtering"
Cohesion: 0.25
Nodes (8): PART 3: Real-Time Hardware Playback Demonstration (Stage 7), From project root:, Hardware Setup & Connection, Host Streaming Harness (`scripts/stream_eeg_uart.py`), Latency Verification & Filter Group Delay Characterization, Physical Board Indicators During Demonstration, Running the Streaming Demo:, UART Binary Streaming Protocol

### Community 34 - "Project Documentation & Reports"
Cohesion: 0.25
Nodes (8): PART 4: Full-Cohort Fixed-Point Quantization LORO (Stage 8), Context & Motivation, Execution & Verification Flow, Expected Results & Consistency Check, Fixed-Point Arithmetic Model, From project root:, LaTeX Comparison Table for Final Report:, Turnkey Execution Prompt for Part 4

### Community 35 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): Real-Time EEG Seizure Detection on FPGA (DWT + Linear SVM), Bit-Exact DWT Verification (`rtl/dwt_db4.v`), Directory Layout & Manifest, Environment Setup, Executive Summary & Verified Results, Hardware Simulation & RTL Verification, Quickstart & Reproduction Guide, Reproducing Tables & Figures from the Report

### Community 36 - "Golden Reference Model"
Cohesion: 0.25
Nodes (8): Golden Reference Model: Multichannel Real-Time EEG Seizure Detector, Architecture & Data Flow, Basic Execution (Both Float and Fixed-Point with Comparison Report), How to Run, Options, Overview, Stage Details, Test Vectors Generated (`golden/vectors/`)

### Community 37 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): AGENT PROMPT: EE2000 EEG Seizure Detection (DWT + linear SVM) - Mid-term execution, Decisions log, Non-negotiable rules, process.md - EE2000 EEG seizure detection work log, process.md protocol (the user reads this to know what was done), Project in 6 lines (so you never lose the thread), Status board, Your role

### Community 38 - "Project Documentation & Reports"
Cohesion: 0.25
Nodes (8): EE2000 Signal Processing — Boolean Board Project Research Report, A. Directly possible on the Boolean Board (no external hardware), B. Requires an external peripheral, C. Impractical for this project, Executive Summary, Project Flier Requirements (extracted directly from the PDF), What I could NOT verify, Xilinx Boolean Board — Verified Capabilities

### Community 39 - "Subject Selection & Rules (S1)"
Cohesion: 0.25
Nodes (8): process.md - EE2000 EEG seizure detection work log, AI-usage ledger, Decisions log, Entry 1 - 2026-10-22 01:40 - Step S0, Entry 2 - 2026-10-22 01:42 - Step S1, Log, Open issues, Status board

### Community 40 - "Wavelet Decomposition (DWT)"
Cohesion: 0.25
Nodes (8): Real-Time EEG Seizure Detection on FPGA (DWT + Linear SVM), Bit-Exact DWT Verification (`rtl/dwt_db4.v`), Directory Layout & Manifest, Environment Setup, Executive Summary & Verified Results, Hardware Simulation & RTL Verification, Quickstart & Reproduction Guide, Reproducing Tables & Figures from the Report

### Community 41 - "Linear SVM Export & Inference"
Cohesion: 0.25
Nodes (8): Top-Tier EE2000 Signal Processing Projects, Acoustic Source Localization (Microphone Array Beamforming), Baseband OFDM Transceiver with Analog Loopback, Live ECG Arrhythmia Classifier (ML for Signal Processing), Live Guitar Multi-Effects Processor, Real-Time 2D FFT Image Spectrum Analyzer, Real-Time Audio Noise Cancellation (LMS Adaptive Filter), Real-Time Voice Disguiser / Pitch Shifter (Phase Vocoder)

### Community 42 - "Viva Defense & Technical Q&A"
Cohesion: 0.29
Nodes (7): EE2000 Final Project: Endsem Definition of Done & Submission Checklist, A. Verilog RTL & Simulation (Stage 6A), B. Vivado Implementation & Timing Closure (Stage 6B), C. Hardware Playback Demonstration (Stage 7), D. Full-Cohort Quantization LORO Study (Stage 8), E. Final Report & Packaging (Stage 9), Pre-Submission Verification Checklist

### Community 43 - "RTL Testbenches & Alarm Logic"
Cohesion: 0.29
Nodes (4): tb_feature_accumulator, feed_dwt_window, tb_feature_accumulator, feed_dwt_window

### Community 44 - "Viva Defense & Technical Q&A"
Cohesion: 0.29
Nodes (7): EE2000 Final Project: Endsem Definition of Done & Submission Checklist, A. Verilog RTL & Simulation (Stage 6A), B. Vivado Implementation & Timing Closure (Stage 6B), C. Hardware Playback Demonstration (Stage 7), D. Full-Cohort Quantization LORO Study (Stage 8), E. Final Report & Packaging (Stage 9), Pre-Submission Verification Checklist

### Community 45 - "Feature Extraction"
Cohesion: 0.38
Nodes (3): extract_record_features(), extract_subband_features(), extract_window_features()

### Community 46 - "Wavelet Decomposition (DWT)"
Cohesion: 0.33
Nodes (6): Discrete Wavelet Transform (DWT), EE2000 Final Project: Endsem Phase Execution Guide, Directory Layout & Document Map, Executive Roadmap & Objectives, Key Milestones & Dates, Quick-Start Guide for Teammates

### Community 47 - "Refractory Alarms"
Cohesion: 0.40
Nodes (3): merge_refractory_alarms(), run_unit_tests(), score_record_events()

## Knowledge Gaps
- **225 isolated node(s):** `alarm_logic`, `iir_biquad`, `svm_classifier`, `uart_rx`, `uart_tx` (+220 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 491 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `stream_hex_vector()` connect `Architecture Changelog & Roadmap` to `Fixed-Point Quantization & LORO`, `Golden Reference Model`, `Submission Audit & Verification`, `Plan Seizure`, `FPGA RTL Architecture`, `FPGA RTL Architecture`, `FPGA RTL Architecture`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `RealDigital Boolean Board` (e.g. with `AGENT PROMPT: EE2000 EEG Seizure Detection (DWT + linear SVM) - Mid-term execution` and `EE2000 Seizure Detector – Antigravity Fix Plan`) actually correct?**
  _`RealDigital Boolean Board` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `alarm_logic`, `iir_biquad`, `svm_classifier` to the rest of the system?**
  _225 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Submission Audit & Verification` be split into smaller, more focused modules?**
  _Cohesion score 0.052214452214452214 - nodes in this community are weakly interconnected._
- **Why does `audit_final_submission()` connect `Submission Audit & Verification` to `Submission Audit & Verification`, `Wavelet Decomposition (DWT)`, `Wavelet Decomposition (DWT)`, `Subject Selection & Rules (S1)`, `Wavelet Decomposition (DWT)`, `Viva Defense & Technical Q&A`, `Submission Audit & Verification`, `Viva Defense & Technical Q&A`, `Viva Defense & Technical Q&A`, `Wavelet Decomposition (DWT)`, `Wavelet Decomposition (DWT)`, `Seizure Validation & Visualizations`, `Wavelet Decomposition (DWT)`, `Seizure Validation & Visualizations`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Should `Architecture Changelog & Roadmap` be split into smaller, more focused modules?**
  _Cohesion score 0.06095791001451379 - nodes in this community are weakly interconnected._
- **Why does `top_seizure_detector` connect `RTL Testbenches & Alarm Logic` to `Viva Defense & Technical Q&A`, `EEG Preprocessing & Filtering`, `Submission Audit & Verification`, `Wavelet Decomposition (DWT)`, `Wavelet Decomposition (DWT)`, `Viva Defense & Technical Q&A`, `EEG Preprocessing & Filtering`, `Wavelet Decomposition (DWT)`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._