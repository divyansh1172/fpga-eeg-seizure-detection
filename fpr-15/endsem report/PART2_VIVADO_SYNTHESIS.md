# PART 2: Vivado Synthesis, Implementation & Timing Closure (Stage 6B)
**Lead Owner:** Member 4 (Vivado Synthesis & Implementation Lead)  
**Goal:** Run non-project batch Vivado synthesis, achieve 100 MHz timing closure, extract post-implementation resource utilization and power dissipation, and generate `top_seizure_detector.bit`.

---

## 1. Context & Objectives
In the mid-term report, Table 8 and Table 10 presented *analytical projections* for FPGA resources (projected $\approx 1{,}450$ LUTs, $\approx 1{,}820$ FFs, 2 DSPs, 4 BRAMs).
For the Final Report (due Nov 13), the rubric requires:
1. Measured post-implementation hardware numbers (Slice LUTs, Slice Registers, DSP48E1 slices, 18 Kb BRAMs).
2. Measured Worst Negative Slack ($WNS$) and Worst Hold Slack ($WHS$) verifying 100 MHz timing closure.
3. Total on-chip power dissipation (static + dynamic) calculated using the Vivado Power Analyzer (XPA).
4. Physical bitstream (`top_seizure_detector.bit`) for board programming.

---

## 2. Non-Project Batch Tcl Synthesis Flow
Rather than clicking manually in the Vivado GUI, we provide an automated non-project Tcl script: `scripts/run_vivado_synth.tcl`.
This script runs synthesis, optimization, placement, routing, timing analysis, power estimation, and bitstream generation from the command line in 2–4 minutes.

### 2.1 How to Run Batch Synthesis
Open a Vivado command prompt or standard terminal with Vivado on your PATH:
```powershell
# From the project root:
vivado -mode batch -source "endsem report/scripts/run_vivado_synth.tcl"
```
Or in Windows PowerShell:
```powershell
& "C:\Xilinx\Vivado\2023.1\bin\vivado.bat" -mode batch -source "endsem report\scripts\run_vivado_synth.tcl"
```

### 2.2 Generated Output Files in `results/`
The automated script writes all required metrics to `results/`:
- `results/vivado_utilization_placed.rpt`: Slice LUTs, Slice Registers, DSPs, BRAMs.
- `results/vivado_timing_summary.rpt`: Setup and hold timing slacks ($WNS$, $WHS$).
- `results/vivado_power_report.rpt`: Total on-chip power, clock power, logic power, quiescent power.
- `results/top_seizure_detector.bit`: Ready-to-program bitstream for the Boolean Board.

---

## 3. Physical Pin Constraints (`rtl/boolean_board.xdc`)
The pin constraints file `endsem report/rtl/boolean_board.xdc` contains verified package pin mappings for the RealDigital Boolean Board (`xc7s50csga324-1`):
- **Clock:** `F14` (`LVCMOS33`, $10.0\text{ ns}$ period / $100\text{ MHz}$).
- **Reset Button:** `J2` (`BTN0`, active-high synchronous reset).
- **UART RX:** `V15` (`LVCMOS33`, from onboard CP2102N USB-UART bridge).
- **UART TX:** `W15` (`LVCMOS33`).
- **Alarm LED:** `A4` (`LED15`, active-high alarm strobe).
- **RGB Status LED:** `V6` (Red), `U6` (Green), `U7` (Blue).
- **Slide Switches:** `V2` (`SW0`), `U2` (`SW1`).
- **7-Segment Display:** Anodes `D5`, `C4`, `B2`, `B1`, `A1`, `F4`, `E4`, `D4`; Cathodes `D7`, `C5`, `A5`, `B7`, `A7`, `D6`, `B5`, `A6`.

---

## 4. Resource & Timing Verification Checklist
After the Vivado run finishes, verify that:
1. **Timing Slack ($WNS$):** $WNS > 0.000\text{ ns}$. (Target: $WNS \ge 1.50\text{ ns}$ at 100 MHz).
2. **DSP48E1 Slices:** Exactly $\le 2$ slices utilized (one for DWT convolution, one for SVM dot product).
3. **18 Kb BRAM Blocks:** Exactly $\le 4$ blocks utilized (circular history buffer + SVM weights).
4. **Slice LUTs:** $< 2{,}000$ ($< 6.1\%$ of 32,600).
5. **Total On-Chip Power:** Record total power in mW for Section 9 of the Final Report.

---

## 5. Turnkey Execution Prompt for Part 2

```markdown
### PROMPT TO EXECUTE PART 2:
You are the Vivado implementation specialist for EE2000 Team 15.
Please execute the batch synthesis and implementation pipeline:
1. Ensure `rtl/boolean_board.xdc` matches the RealDigital Boolean Board pinout.
2. Execute `vivado -mode batch -source "endsem report/scripts/run_vivado_synth.tcl"`.
3. Parse the generated reports:
   - Extract final Slice LUTs, Slice FFs, DSP48E1 slices, and 18 Kb BRAMs from `results/vivado_utilization_placed.rpt`.
   - Verify Worst Negative Slack (WNS) and Worst Hold Slack (WHS) from `results/vivado_timing_summary.rpt`.
   - Extract total on-chip power (mW) from `results/vivado_power_report.rpt`.
4. Update Table 8 and Table 10 in `report/final-15.tex` with the measured post-implementation numbers.
5. Log all exact numbers, execution commands, and timing margins in `process.md`.
```
