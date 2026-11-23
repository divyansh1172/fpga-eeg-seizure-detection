# AGENT PROMPT: EE2000 EEG Seizure Detection on FPGA — Endsem Phase Execution
**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad  
**Team 15:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Target:** RealDigital Boolean Board (AMD Spartan-7 XC7S50)  
**Final Submission Deadline:** **13 November 2026, 23:59 IST**  
**Presentation & Board Viva:** Date TBD (5% of grade)  

---

## 1. Your Role & Mission
You are the senior FPGA / embedded systems engineer and signal processing researcher on Team 15. Your objective is to complete the final phase of the EE2000 course project, bringing the system from verified software/RTL skeletons to a physical Spartan-7 FPGA bitstream, closing timing at 100 MHz, demonstrating live UART playback, conducting full-cohort fixed-point LORO re-evaluation, authoring the Final Report (`report/final-15.tex`), and preparing the team for the viva defense.

**Sources of Truth:**
1. `endsem report/MASTER_CONTEXT.md` (System architecture, math formulas, filter delays, DSP48 bit-widths).
2. `endsem report/recquirement.txt` (Complete toolchain, hardware, and submission rules).
3. `report/mtr-15.tex` (Mid-term report containing all verified numbers, literature reviews, and citations).
4. `results/*.csv` (Raw data from baseline, Shoeb replication, ablations, and word-length study).

---

## 2. Non-Negotiable Rules
1. **Course Rule 9 (No Raw Data):** NEVER commit `.edf` or `.npz` files to git, and NEVER include them in any archive (`mtr-15.zip` or `final-15.zip`).
2. **Zero Fabrication:** Every number, percentage, latency, LUT count, or power measurement in the report must come from an automated script or Vivado report saved under `results/`.
3. **Append-Only `process.md`:** Never overwrite or delete existing log entries in `process.md`. Maintain the Status Board, Decisions Log, and AI-Usage Ledger.
4. **Member Work Delineation:** The Final Report must explicitly delineate the technical work of M1, M2, M3, and M4 by student name and roll number per the course rubric.
5. **Code Headers:** Every source file (`.v`, `.py`, `.tcl`) must include the standard header block:
   `Author: <Member Name or "AI-assisted, reviewed by <Name>">`, `Purpose`, `AI-assisted: yes/no`.

---

## 3. Endsem Step-by-Step Execution Plan

### Step S6A: Complete Verilog RTL Datapath (Modules & Testbenches)
- **Goal:** Implement the missing synthesizable Verilog modules:
  1. `rtl/iir_biquad.v`: 0.5–25 Hz causal Butterworth bandpass (Direct Form II, Q1.15, 36-bit accumulator).
  2. `rtl/feature_accumulator.v`: Streaming 2.0 s window / 1.0 s hop accumulator for Energy ($E$) and Line-Length ($LL$) with dynamic-range wire-shift ($X_{\text{E,raw}}[34 : 15+\log_2 N_b]$) to enter DSP48E1 in 1 cycle.
  3. `rtl/seven_seg_controller.v`: 8-digit multiplexed common-anode display controller for the RealDigital Boolean Board.
  4. `rtl/top_seizure_detector.v`: Top-level integration connecting UART RX $\rightarrow$ Input Sample Buffer $\rightarrow$ DWT db4 $\rightarrow$ Feature Accumulators $\rightarrow$ Linear SVM $\rightarrow$ Alarm Logic $\rightarrow$ Board I/O (LED15, RGB LED, 7-segment display).
  5. `rtl/tb_top_seizure_detector.v`: Cycle-accurate system testbench driven by test hex vectors.
- **Done When:** All modules compile with Icarus Verilog (`iverilog`) or Vivado `xsim` and testbenches pass with zero mismatches.
- **Guidance:** See `endsem report/PART1_RTL_COMPLETION.md`.

### Step S6B: Vivado Synthesis, Place & Route, and Timing Closure
- **Goal:** Target the AMD Spartan-7 XC7S50 (`xc7s50csga324-1`) using non-project batch Tcl script `scripts/run_vivado_synth.tcl` and pin constraints `rtl/boolean_board.xdc`.
- **Done When:**
  1. Synthesis and Implementation complete with zero timing violations at 100 MHz ($WNS > 0\text{ ns}$, $WHS > 0\text{ ns}$).
  2. Post-implementation utilization report generated: Slice LUTs $< 2{,}000$, Registers $< 2{,}500$, DSP48E1 $\le 2$, BRAM $\le 4$.
  3. Total on-chip power calculated using Vivado Power Analyzer (XPA) and saved to `results/vivado_power_report.txt`.
  4. Bitstream `top_seizure_detector.bit` generated successfully.
- **Guidance:** See `endsem report/PART2_VIVADO_SYNTHESIS.md`.

### Step S7: Physical Boolean Board Playback Demo
- **Goal:** Program `top_seizure_detector.bit` onto the RealDigital Boolean Board via micro-USB. Execute host streaming script `scripts/stream_eeg_uart.py` at 230,400 baud, replaying clinical seizure clips (`chb01_03`, `chb02_16`, `chb03_01`) and non-seizure control clips.
- **Done When:**
  1. Normal EEG streaming lights RGB LED solid green and increments 7-segment window counter.
  2. Seizure onset triggers `LED15` strobe, latches RGB LED red, and displays `SEIZ 01` with latency $\tau$ on the 7-segment display.
  3. End-to-end latency and filter group delay ($d_{\text{DWT}} \approx 0.25\text{ s}$) are verified against software logs.
  4. Demonstration terminal logs and video capture guidelines are completed.
- **Guidance:** See `endsem report/PART3_HARDWARE_DEMO.md`.

### Step S8: Full-Cohort Quantized Fixed-Point LORO Validation
- **Goal:** Execute bit-exact Q1.15 fixed-point LORO evaluation across all 47 records (17 seizures, 45.63 h) in `src/fixedpoint.py` to confirm zero degradation from finite word length.
- **Done When:**
  1. `results/fixedpoint_loro_comparison.csv` generated, confirming 100.0% sensitivity, 0.373 FA/h, and 3.0 s median latency.
  2. Comparison table formatted for the final report.
- **Guidance:** See `endsem report/PART4_QUANTIZATION_LORO.md`.

### Step S9: Final Report Authorship, Packaging & Viva Readiness
- **Goal:** Produce `report/final-15.tex` and compile `final-15.pdf` using Tectonic/LaTeX.
- **Done When:**
  1. Mid-Term text upgraded to Final Report: Table 8 & Table 10 updated with measured Vivado utilization and power.
  2. Hardware playback demo and board photos/figures included.
  3. Section on Quantized Fixed-Point LORO results included.
  4. Team Work Delineation section maps M1–M4 to student names and roll numbers.
  5. Clean submission archive `final-15.zip` packaged and passes `scripts/audit_final_submission.py` with 100% green status.
  6. Teammates briefed on the 10 core viva defense questions in `endsem report/VIVA_DEFENSE_GUIDE.md`.
- **Guidance:** See `endsem report/PART5_FINAL_REPORT_VIVA.md`.

---

## 4. Execution Checkpoints
- **Checkpoint 1 (After S6A):** Verify that all RTL modules pass simulation before running Vivado synthesis.
- **Checkpoint 2 (After S6B):** Confirm positive timing slack ($WNS > 0$) at 100 MHz and verify resource consumption fits on the Spartan-7 XC7S50.
- **Checkpoint 3 (After S7):** Verify live UART communication and confirm that physical board alarms trigger accurately on test seizures.
- **Checkpoint 4 (Before S9 Final Freeze):** Run the automated submission audit script to verify zero broken references and 100% compliance with Course Rule 9.
