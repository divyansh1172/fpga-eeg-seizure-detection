# EE2000 Final Project: Team Work Delineation & Code Ownership
**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad  
**Team 15:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Mandatory Rubric Requirement:** Course flier states: *"The work done by each team member must be clearly delineated and the code written by each team member must be appropriately commented."*

---

## 1. Member Ownership Matrix

| Member | Primary Role | Code & Files Owned | Key Deliverables & Responsibilities | Viva Defense Specialty |
|---|---|---|---|---|
| **Member 1 (M1)** | Data Engineering, Host Demo & Report Lead | `src/data_io.py`<br>`src/config.py`<br>`scripts/stream_eeg_uart.py`<br>`report/final-15.tex` | • CHB-MIT record parsing & manifests<br>• Host UART binary streaming harness<br>• End-to-end latency measurements<br>• Final report drafting & packaging | Dataset protocol, channel montages, streaming latency, UART protocol |
| **Member 2 (M2)** | Signal Processing & Machine Learning Lead | `src/dwt.py`<br>`src/features.py`<br>`src/train.py`<br>`src/ablate.py`<br>`src/fixedpoint.py`<br>`src/shoeb_baseline.py` | • Causal IIR filter & db4 DWT math<br>• LORO cross-validation loop<br>• Shoeb baseline replication<br>• Full-cohort fixed-point LORO study<br>• Ablation studies ($k$, features, $C$) | Wavelet math, feature formulation, LORO fold isolation, SQNR, statistical CIs |
| **Member 3 (M3)** | Hardware RTL Architecture & DSP48E1 Specialist | `rtl/dwt_db4.v`<br>`rtl/svm_classifier.v`<br>`rtl/feature_accumulator.v`<br>`rtl/iir_biquad.v`<br>`rtl/alarm_logic.v`<br>`rtl/tb_*.v` | • Synthesizable Verilog RTL datapath<br>• Dynamic-range wire-shift for DSP48E1<br>• 176-cycle pipelined SVM classifier<br>• Cycle-accurate simulation testbenches<br>• Hex vector bit-exact verification | Verilog FSMs, DSP48 multiplier port limits, Q1.15 bit-widths, accumulator sizing |
| **Member 4 (M4)** | Vivado Synthesis, Implementation & Board Demo Lead | `rtl/boolean_board.xdc`<br>`rtl/top_seizure_detector.v`<br>`rtl/seven_seg_controller.v`<br>`scripts/run_vivado_synth.tcl`<br>`scripts/program_board.tcl` | • Physical pin constraints (XDC)<br>• Non-project batch Tcl synthesis<br>• 100 MHz timing closure ($WNS > 0$)<br>• Vivado Power Analyzer (mW)<br>• 7-segment display & LED controller<br>• Live Boolean Board demonstration | Clock domain timing, synthesis reports, Spartan-7 architecture, board demo |

---

## 2. Mandatory Code Commenting Guidelines
Per the rubric, every source file must feature complete comments explaining non-trivial logic. Each teammate must ensure their files include:

### 2.1 File Header Block (Required on all `.py`, `.v`, `.tcl`)
```verilog
/*
 * Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
 * Team: 15
 * Author: Member 3 (Name, Roll No: EE24BTECH...)
 * Purpose: Synthesizable 8-tap Daubechies-4 analysis filter bank with decimation-by-2
 * AI-assisted: Yes (Verilog scaffolding generated with Antigravity, reviewed and verified by Member 3)
 */
```

### 2.2 In-Line Function & Equation Explanations
- Always annotate the physical reason for bit-width selections, wire truncations, or shift counts.
- Example:
  ```verilog
  // In fixed-point Q1.15, squaring produces Q2.30.
  // We drop the 15 fractional LSBs and shift by log2(Nb) = 6 bits for D3.
  // This normalizes 38-bit Energy down to 19 bits (0 LUT cost), fitting the 25-bit DSP48 port.
  wire signed [18:0] energy_d3_norm = energy_acc[34:21];
  ```

---

## 3. Team Member Viva Defense Preparation
During the viva, examiners frequently ask each member individual questions to verify ownership:
- **For Member 1:** Be prepared to explain how the 22 bipolar channels are extracted from CHB-MIT EDF headers, why duplicate `T8-P8` was removed, and how the UART packet protocol guarantees lossless sample delivery at 230,400 baud.
- **For Member 2:** Be prepared to derive the theoretical SQNR equation ($6.02B + 1.76\text{ dB}$), explain why McNemar's test yields $p \approx 0.50$ between Shoeb and the proposed pipeline, and why Energy and Line-Length are strictly sign-invariant across channels `T7-P7` and `P7-T7`.
- **For Member 3:** Be prepared to explain the internal architecture of the Xilinx DSP48E1 slice ($25 \times 18$ multiplier + 48-bit accumulator), how offline weight folding saves a hardware divider, and why the 5-level db4 cascade has a 218-sample causal span but only $\approx 0.25\text{ s}$ group delay.
- **For Member 4:** Be prepared to open the Vivado timing report, point to the Worst Negative Slack ($WNS$), explain how the 100 MHz clock is routed through global clock buffers (BUFG), and show how the 8-digit multiplexed display avoids visible flicker.
