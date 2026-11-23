# PART 1: RTL Completion & Top-Level Integration (Stage 6A)
**Lead Owners:** Member 3 (RTL Datapath) & Member 4 (Board I/O)  
**Goal:** Complete all missing synthesizable Verilog RTL modules, wire the end-to-end streaming datapath, and verify cycle-accurate behavior in simulation.

---

## 1. Context & Architecture Status
At the mid-term milestone, four synthesizable modules were created:
- `rtl/dwt_db4.v`: Single-level Daubechies-4 analysis filter pair (verified against bit-exact hex vectors).
- `rtl/svm_classifier.v`: 176-cycle pipelined Linear SVM decision engine with offline folded weights.
- `rtl/alarm_logic.v`: $k$-window temporal alarm FSM with 30 s refractory suppression.
- `rtl/uart_rx.v`: 230,400-baud UART receiver with double-flop metastability synchronization.

To complete the synthesizable hardware system for the Spartan-7 XC7S50, three missing modules and the top-level integration must be implemented:
1. `rtl/iir_biquad.v`: Front-end $0.5\text{--}25\text{ Hz}$ causal IIR bandpass filter.
2. `rtl/feature_accumulator.v`: Sub-band Energy ($E$) and Line-Length ($LL$) window accumulator with dynamic-range wire-shifting.
3. `rtl/seven_seg_controller.v`: 8-digit multiplexed common-anode display controller for the Boolean Board.
4. `rtl/top_seizure_detector.v`: Top-level system wiring all blocks to physical board pins.
5. `rtl/tb_top_seizure_detector.v`: Top-level simulation testbench.

---

## 2. Technical Specifications for Each Module

### 2.1 Front-End Causal IIR Bandpass (`rtl/iir_biquad.v`)
- **Filter Topology:** Direct Form II Transposed Biquad (2 cascaded 2nd-order sections = 4th order Butterworth).
- **Cutoffs:** $0.5\text{ Hz}$ high-pass, $25\text{ Hz}$ low-pass at $f_s = 256\text{ Hz}$.
- **Arithmetic:** Signed 16-bit Q1.15 input/output, signed 16-bit Q2.14 filter coefficients, 36-bit accumulator to eliminate internal overflow.
- **State Handling:** Synchronous `reset_state` input asserts zero-initialization at the start of each recording.

### 2.2 Feature Accumulators with Wire-Shift (`rtl/feature_accumulator.v`)
- **Input:** Valid wavelet detail ($D_3, D_4, D_5$) and approximation ($A_5$) samples from the DWT filter bank.
- **Hop & Window Management:** Ping-pong double-buffer accumulating across $T = 2.0\text{ s}$ (512 samples) with hop $h = 1.0\text{ s}$ (256 samples).
- **Line-Length Accumulator ($LL$):** Computes $\sum |c[n] - c[n-1]|$ over $N_b - 1$ samples. Sum width is 23 bits, fitting natively into the 25-bit port of the DSP48E1 slice.
- **Energy Accumulator ($E$):** Computes $\sum c[n]^2$ over $N_b$ samples. Squaring Q1.15 produces Q2.30; accumulating $N_b \le 64$ samples produces a 38-bit sum.
- **Dynamic-Range Wire-Shift:**
  ```verilog
  // Hardware wire-shift (0 LUT cost) normalizes 38-bit Energy to <= 19 bits
  // Dropping 15 fractional LSBs and shifting by log2(Nb):
  wire signed [18:0] energy_normalized =
      (subband_id == 2'd0) ? energy_acc[34:21] : // D3 (Nb=64, shift=6+15=21)
      (subband_id == 2'd1) ? energy_acc[33:20] : // D4 (Nb=32, shift=5+15=20)
      (subband_id == 2'd2) ? energy_acc[32:19] : // D5 (Nb=16, shift=4+15=19)
                             energy_acc[32:19];   // A5 (Nb=16, shift=4+15=19)
  ```
  This brings Energy onto the exact same numerical scale as Line-Length, enabling both to enter the single DSP48E1 multiplier in 1 clock cycle!

### 2.3 Boolean Board 7-Segment Controller (`rtl/seven_seg_controller.v`)
- **Target Display:** Dual 4-digit common-anode 7-segment display (8 digits total on RealDigital Boolean Board).
- **Refresh Frequency:** 100 MHz divided to $1\text{ kHz}$ ($125\text{ Hz}$ per digit refresh rate, flicker-free).
- **Display Modes:**
  * Digits 7..4: Displays current channel ID or elapsed streaming time (e.g., `CH 01` or `T 3004`).
  * Digits 3..0: Normal streaming displays `IDLE`; on seizure alarm assertion displays `SEIZ` or alarm count `AL 01`.
  * Outputs: `anode[7:0]` (active-low), `seg[6:0]` (cathodes active-low $A\text{--}G$), `dp` (decimal point).

### 2.4 Top-Level System Wrapper (`rtl/top_seizure_detector.v`)
- **Port Interface:**
  * `clk`: 100 MHz system clock from Pin `F14`.
  * `rst_n`: Active-low system reset from Pushbutton `BTN0` (Pin `J2`).
  * `uart_rxd`: Serial input from USB-UART bridge (Pin `V15`).
  * `sw[1:0]`: Slide switches selecting alarm persistence $k \in \{1, 2, 3, 5\}$.
  * `led[15:0]`: `led[15]` indicates Seizure Alarm Strobe; `led[7:0]` show active channel ID.
  * `rgb0_r`, `rgb0_g`, `rgb0_b`: RGB Status LED (Green = OK streaming; Red = Seizure Alarm).
  * `anode[7:0]`, `seg[6:0]`, `dp`: 7-Segment Display interface.

---

## 3. Turnkey Execution Prompt for Part 1

```markdown
### PROMPT TO EXECUTE PART 1:
You are the RTL specialist for EE2000 Team 15.
Please write and verify the missing Verilog modules in `rtl/`:
1. `rtl/iir_biquad.v`: Synthesizable 4th-order causal Butterworth IIR bandpass (0.5-25 Hz) in Direct Form II Transposed, Q1.15 arithmetic, 36-bit accumulator, synchronous reset.
2. `rtl/feature_accumulator.v`: Dual-feature accumulator for Energy (with dynamic-range wire shift dropping 15 fractional LSBs) and Line-Length across 2.0 s / 1.0 s hop windows.
3. `rtl/seven_seg_controller.v`: 8-digit multiplexed common-anode display controller for the RealDigital Boolean Board.
4. `rtl/top_seizure_detector.v`: Top-level integration connecting `uart_rx`, `iir_biquad`, `dwt_db4`, `feature_accumulator`, `svm_classifier`, `alarm_logic`, and `seven_seg_controller` to physical Boolean Board I/O.
5. `rtl/tb_top_seizure_detector.v`: System testbench feeding streaming EEG frames and asserting alarm verification.

Ensure all modules include standard team headers, follow clean synchronous reset rules, and simulate without errors under Icarus Verilog or Vivado xsim.
```
