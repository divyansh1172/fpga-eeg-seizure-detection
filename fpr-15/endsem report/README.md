# EE2000 Final Project: Endsem Phase Execution Guide
**Course:** EE2000 Signal Processing, Fall 2026 | Indian Institute of Technology Hyderabad  
**Team 15:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Target:** RealDigital Boolean Board (AMD Spartan-7 XC7S50)  
**Final Submission Deadline:** **13 November 2026, 23:59 IST**  
**Presentation & Board Viva:** Date TBD (5% of total grade)

---

## 1. Executive Roadmap & Objectives
Having completed Stages 1 through 5 for the Mid-Term Milestone (100.0% sensitivity, 0.373 FA/h, 3.0 s median latency, Shoeb replication, and 4 verified RTL modules), the Endsem Phase finishes the project and delivers:
1. **Stage 6 (Hardware Synthesis & Timing Closure):** Complete synthesizable Verilog RTL datapath (IIR biquad, feature accumulators, 7-seg controller, top-level integration), synthesize on Spartan-7 XC7S50 at 100 MHz, and close timing with zero violations.
2. **Stage 7 (Live Boolean Board Playback Demo):** Stream continuous EEG data from PC to Boolean Board over 230,400-baud UART and trigger physical alarm indicators (LED15 strobe, flashing red RGB LED, 7-segment display showing latency and event count).
3. **Stage 8 (Full-Cohort Quantization LORO):** Execute bit-exact Q1.15 fixed-point pipeline across all 47 records in Python to prove zero metric degradation from finite word length.
4. **Stage 9 (Final Report & Viva Preparation):** Publish the final report (`final-15.pdf`) using the IEEE CVF two-column template, delineate individual contributions of M1–M4, and prepare the viva defense deck.

---

## 2. Directory Layout & Document Map
Inside `endsem report/`, you will find all necessary context, task breakdowns, execution prompts, starter code, and constraints:

```text
endsem report/
├── README.md                      # This executive guide and roadmap
├── recquirement.txt               # Full technical and hardware requirements for teammates
├── MASTER_CONTEXT.md              # Complete 360-degree mathematical, algorithmic & hardware context
├── AGENT_PROMPT.md                # Turnkey prompt for AI coding agents to execute the phase
├── TEAM_WORK_DELINEATION.md       # Mandatory team contribution statement (M1-M4) for report
├── VIVA_DEFENSE_GUIDE.md          # 10 deep-dive examiner questions & answers for the viva
├── CHECKLIST.md                   # Definition of done and pre-submission audit checklist
│
├── PART1_RTL_COMPLETION.md        # Stage 6A: Verilog datapath, accumulators, top-level + prompt
├── PART2_VIVADO_SYNTHESIS.md      # Stage 6B: Batch Vivado synthesis, timing, power + prompt
├── PART3_HARDWARE_DEMO.md         # Stage 7: Real-time UART playback harness & demo + prompt
├── PART4_QUANTIZATION_LORO.md     # Stage 8: Full-cohort fixed-point LORO re-evaluation + prompt
├── PART5_FINAL_REPORT_VIVA.md     # Stage 9: IEEE CVF final report authorship & packaging + prompt
│
├── rtl/
│   └── boolean_board.xdc          # Master XDC pin constraints for RealDigital Boolean Board
│
└── scripts/
    ├── run_vivado_synth.tcl       # Automated non-project batch synthesis Tcl script
    └── stream_eeg_uart.py         # Python host streaming script for 230,400-baud playback
```

---

## 3. Quick-Start Guide for Teammates
1. **Inspect Requirements:** Read [recquirement.txt](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/recquirement.txt) to verify your Python packages, Vivado installation, and hardware connections.
2. **Review Master Context:** Read [MASTER_CONTEXT.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/MASTER_CONTEXT.md) for full formulas, filter delay math, and DSP48E1 bit-width rules.
3. **Execute by Parts:** Follow the step-by-step modular guides:
   - For Verilog RTL: follow [PART1_RTL_COMPLETION.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/PART1_RTL_COMPLETION.md).
   - For Vivado Synthesis: follow [PART2_VIVADO_SYNTHESIS.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/PART2_VIVADO_SYNTHESIS.md).
   - For Board Demo: follow [PART3_HARDWARE_DEMO.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/PART3_HARDWARE_DEMO.md).
   - For Quantization Study: follow [PART4_QUANTIZATION_LORO.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/PART4_QUANTIZATION_LORO.md).
   - For Final Report & Viva: follow [PART5_FINAL_REPORT_VIVA.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/PART5_FINAL_REPORT_VIVA.md).
4. **Log Everything:** Append every command, result, and decision to `process.md`.
5. **Prepare for Viva:** Study [VIVA_DEFENSE_GUIDE.md](file:///D:/Sem/Sem-3/EE2000%20Project/endsem%20report/VIVA_DEFENSE_GUIDE.md).

---

## 4. Key Milestones & Dates
| Date | Milestone | Key Deliverable | Owner |
|---|---|---|---|
| **Nov 1 – Nov 5** | Stage 6: RTL Completion & Synthesis | `top_seizure_detector.bit`, timing closure report | M3, M4 |
| **Nov 6 – Nov 8** | Stage 7: Physical Board Demo | 230,400-baud UART streaming, LED/7-seg demo | M1, M4 |
| **Nov 9 – Nov 10** | Stage 8: Quantized LORO Study | `results/fixedpoint_loro_comparison.csv` | M2 |
| **Nov 11 – Nov 12** | Stage 9: Final Report Draft | `report/final-15.tex`, `final-15.pdf` | M1 + All |
| **Nov 13 (23:59)** | Final Submission Freeze | `final-15.pdf`, `final-15.zip`, passing audit | All |
| **TBD (Mid-Nov)** | In-Person Presentation & Viva | Live Boolean Board demonstration | All |
