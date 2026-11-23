# EE2000 Final Project: Endsem Definition of Done & Submission Checklist
**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad  
**Team 15:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Final Submission Deadline:** **13 November 2026, 23:59 IST**  

---

## 1. Pre-Submission Verification Checklist

### A. Verilog RTL & Simulation (Stage 6A)
- [ ] All synthesizable Verilog modules exist in `rtl/`:
  * `rtl/iir_biquad.v`
  * `rtl/dwt_db4.v`
  * `rtl/feature_accumulator.v`
  * `rtl/svm_classifier.v`
  * `rtl/alarm_logic.v`
  * `rtl/seven_seg_controller.v`
  * `rtl/uart_rx.v`
  * `rtl/top_seizure_detector.v`
- [ ] All testbenches (`rtl/tb_*.v`) compile and pass without errors under Icarus Verilog or Vivado `xsim`.
- [ ] Standard author header comment blocks present on all Verilog files.
- [ ] Zero unsimulated or placeholder code remains.

### B. Vivado Implementation & Timing Closure (Stage 6B)
- [ ] Non-project batch synthesis script `scripts/run_vivado_synth.tcl` executes successfully.
- [ ] Pin constraints `rtl/boolean_board.xdc` mapped correctly to Spartan-7 XC7S50.
- [ ] Timing closure verified at 100 MHz: Worst Negative Slack ($WNS > 0.000\text{ ns}$), Worst Hold Slack ($WHS > 0.000\text{ ns}$).
- [ ] Post-implementation utilization confirmed: Slice LUTs $< 2{,}000$, Registers $< 2{,}500$, DSP48E1 $\le 2$, 18 Kb BRAM $\le 4$.
- [ ] Total on-chip power calculated using Vivado Power Analyzer (XPA) and saved to `results/vivado_power_report.rpt`.
- [ ] Bitstream `results/top_seizure_detector.bit` generated cleanly.

### C. Hardware Playback Demonstration (Stage 7)
- [ ] RealDigital Boolean Board programmed with `top_seizure_detector.bit`.
- [ ] Python streaming harness `scripts/stream_eeg_uart.py` connects at 230,400 baud.
- [ ] Playback of clinical seizure clip (`chb01_03`) asserts `LD15` strobe and turns RGB LED solid Red at $t = 3004\text{ s}$ ($k=3$).
- [ ] 7-segment display displays latency $\tau = 8.0\text{ s}$ and alarm count.
- [ ] 30-second post-alarm refractory blanking prevents duplicate triggers.
- [ ] Terminal playback log saved to `results/uart_demo_playback.log`.
- [ ] Board demo photos and short 2-minute demonstration video saved in `results/demo/`.

### D. Full-Cohort Quantization LORO Study (Stage 8)
- [ ] `scripts/run_fixedpoint_loro.py` executed across all 47 CHB-MIT records.
- [ ] Output `results/fixedpoint_loro_comparison.csv` confirms:
  * Sensitivity: 100.0% (17/17 seizures)
  * False-Alarm Rate: 0.373 FA/h
  * Median Latency: 3.0 s
- [ ] Comparison table included in Section 7.5 of the Final Report.

### E. Final Report & Packaging (Stage 9)
- [ ] `report/final-15.tex` authored using standard IEEE CVF two-column conference template.
- [ ] Compiled with Tectonic/LaTeX to `final-15.pdf`:
  * Zero broken citations or unresolved `[?]` / `??` references.
  * Table 8 and Table 10 updated with measured Vivado utilization and power.
  * Section 8 merged into Section 9.
  * Section 10 added with hardware demo protocol, latency, and board photos.
  * Section 12 explicitly delineates M1, M2, M3, and M4 by student name and roll number.
  * AI Tool Usage Ledger updated and complete.
- [ ] Packaging script `scripts/package_final_submission.py` generates `final-15.zip`.
- [ ] **Course Rule 9 Verified:** Zero `.edf` or `.npz` files in `final-15.zip` or git.
- [ ] Audit script `scripts/audit_final_submission.py` passes with 100% green status.
- [ ] `process.md` contains complete, append-only log entries documenting every step.
