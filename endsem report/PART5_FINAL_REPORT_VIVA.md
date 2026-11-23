# PART 5: Final Report Authorship, Packaging & Viva Readiness (Stage 9)
**Lead Owners:** Member 1 (Report Lead) & All Team Members  
**Goal:** Upgrade the report to `report/final-15.tex`, compile `final-15.pdf`, delineate individual contributions (M1–M4) by student name/roll number, package `final-15.zip` adhering to Course Rule 9, and prepare for the viva defense.

---

## 1. Compliance with the EE2000 Final Project Rubric
The course flier specifies four mandatory requirements for the Final Report milestone (13.11.2026, 5% of grade):
1. **Build on Previous Reports:** Present algorithm, comprehensive experimental results, hardware implementation, and conclusions in the IEEE CVF two-column format.
2. **Mandatory Team Work Delineation:** The work done by each team member must be clearly delineated, and each member's code must be appropriately commented.
3. **Submit Complete Code & Artifacts:** All synthesizable Verilog RTL, Python pipelines, testbenches, and verification scripts must be submitted in a clean archive (`final-15.zip`).
4. **AI Usage Disclosure & Citations:** Disclose all AI tools used, cite them appropriately, and be prepared to defend all content in the live viva.

---

## 2. Key Upgrades from Mid-Term (`mtr-15`) to Final Report (`final-15`)

| Report Section | Mid-Term Status (`mtr-15.tex`) | Final Report Upgrade (`final-15.tex`) |
|---|---|---|
| **Title & Milestone** | Mid-Term Project Report | Final Project Report (EE2000 Fall 2026, IIT Hyderabad) |
| **Hardware Resources (Table 8 & Table 10)** | Analytical projections (estimated $\approx 1{,}450$ LUTs, 4.45\%) | **Measured post-implementation** numbers from Vivado placed/routed reports |
| **FPGA Power Dissipation** | Not characterized | **Measured total on-chip power (mW)** from Vivado Power Analyzer (XPA) |
| **Timing Closure** | Scheduled for Stage 6 | **Verified 100 MHz timing closure** with explicit $WNS > 0$ and $WHS > 0$ margins |
| **Hardware Playback Demo** | High-level roadmap | **Dedicated Section 10:** UART streaming protocol, observed latency, and Boolean Board demo figures |
| **Quantization Study** | Clip-level SQNR only | **Table 7 expanded:** Full-cohort LORO cross-validation under bit-exact 16-bit fixed-point arithmetic |
| **Section 8 Pointer** | Standalone 2-sentence pointer to Fig. 4 | **Merged into opening of Section 9**, eliminating redundant micro-section |
| **Team Work Delineation** | Anonymized M1–M4 in Table 11 | **Full Section 12:** Mapping M1–M4 to team member names, roll numbers, code ownership, and responsibilities |

---

## 3. Team Member Work Delineation (Template for Section 12)
Per the rubric requirement, replace the anonymized tags with your real team details:

```latex
\section{Team Work Delineation and Contributions}
\label{sec:contributions}
Scores for EE2000 are awarded team-wise, with individual contributions delineated as follows:
\begin{itemize}
    \item \textbf{Member 1 (Name, Roll No: EE24BTECH...):} Data Engineering, Host Demo Harness, and Report Lead. Authored PhysioNet summary and EDF parsers (\texttt{src/data\_io.py}, \texttt{src/config.py}), automated dataset manifest generation, designed the host UART binary streaming harness (\texttt{scripts/stream\_eeg\_uart.py}), and led overall report authorship and packaging.
    \item \textbf{Member 2 (Name, Roll No: EE24BTECH...):} Signal Processing, Machine Learning, and Quantization Lead. Developed causal IIR bandpass filter, 5-level dyadic db4 DWT, and dual-feature extraction (\texttt{src/dwt.py}, \texttt{src/features.py}). Implemented the LORO cross-validation loop and ablation studies (\texttt{src/train.py}, \texttt{src/ablate.py}), replicated the Shoeb baseline (\texttt{src/shoeb\_baseline.py}), and conducted full-cohort fixed-point LORO validation (\texttt{src/fixedpoint.py}).
    \item \textbf{Member 3 (Name, Roll No: EE24BTECH...):} Hardware RTL Architecture and DSP48E1 Specialist. Hand-crafted synthesizable Verilog RTL for the 8-tap db4 DWT analysis filter bank (\texttt{rtl/dwt\_db4.v}), pipelined linear SVM classifier (\texttt{rtl/svm\_classifier.v}), feature accumulators with dynamic-range wire-shift, and front-end IIR biquad cascade (\texttt{rtl/iir\_biquad.v}). Authored cycle-accurate testbench harnesses and verified zero mismatch against golden hex vectors.
    \item \textbf{Member 4 (Name, Roll No: EE24BTECH...):} Vivado Synthesis, Board Integration, and Demo Lead. Created physical pin constraints (\texttt{rtl/boolean\_board.xdc}) and automated non-project Tcl batch synthesis scripts (\texttt{scripts/run\_vivado\_synth.tcl}). Closed timing at 100~MHz on the Spartan-7 XC7S50, generated bitstreams, ran Vivado Power Analyzer, and designed the 8-digit multiplexed 7-segment display and LED status controller (\texttt{rtl/seven\_seg\_controller.v}) for the physical Boolean Board demo.
\end{itemize}
```

---

## 4. Packaging and Pre-Submission Audit
1. Recompile `final-15.pdf`:
   ```powershell
   cd report
   ..\bin\tectonic.exe final-15.tex
   ```
2. Package `final-15.zip`:
   ```powershell
   python scripts/package_final_submission.py
   ```
3. Run the automated audit script:
   ```powershell
   python scripts/audit_final_submission.py
   ```
   Must output: `[SUCCESS] Zero errors found across all deliverables, code, and RTL! 100% submission ready.`

---

## 5. Turnkey Execution Prompt for Part 5

```markdown
### PROMPT TO EXECUTE PART 5:
You are the final report editor and submission lead for EE2000 Team 15.
Please execute the final report authorship, packaging, and audit:
1. Create `report/final-15.tex` by upgrading `report/mtr-15.tex`:
   - Update title to Final Project Report.
   - Insert measured Vivado post-implementation numbers and power in Table 8 and Table 10.
   - Add Section 10: Real-Time Hardware Playback Demonstration with UART protocol and board photographs.
   - Add full-cohort fixed-point LORO comparison in Section 7.5.
   - Merge Section 8 into Section 9.
   - Add Section 12: Team Work Delineation mapping M1–M4 to student names and roll numbers.
2. Compile `final-15.pdf` using Tectonic; verify zero broken references or "[?]".
3. Package `final-15.zip` adhering strictly to Course Rule 9 (zero .edf/.npz files).
4. Run `scripts/audit_final_submission.py` to confirm 100% compliance.
5. Log all final actions in `process.md`.
```
