# Phase 1 — Potential Issues, Technical Risks, and Engineering Concerns

This document details all potential engineering concerns, arithmetic discrepancies, hardware-software mismatches, synthesis inefficiencies, and verification gaps identified during the technical audit of the 22-channel FPGA seizure detection project.

Every finding is categorized by severity:
- **Critical (P0):** Algorithmic discrepancies, verification gaps that invalidate performance claims, or broken test infrastructure.
- **High Severity (P1):** Architectural and synthesis bottlenecks, critical timing risks, massive resource waste, or unverified physical hardware claims.
- **Medium Severity (P2):** Fixed-point scaling nuances, throughput margins, pinout documentation discrepancies, or boundary transients.
- **Low Severity / Code Hygiene (P3):** Repository organization, code style, uncommitted Git state, or non-critical testbench shortcuts.

Each entry explicitly states whether it is a **Confirmed Fact**, a **Suspected Issue**, or an **Unknown**, accompanied by file paths, line references, mathematical/architectural explanations, and recommended remediation strategies.

---

## 1. Critical Issues (P0)

### Issue 1.1: Training vs. Hardware Window Duration Mismatch (2.0s vs. 1.0s)
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [src/config.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/config.py#L62-L65) (lines 62–65)
  - [src/train.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/train.py#L35-L50) (lines 35–50)
  - [src/features.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/features.py#L50-L65) (lines 50–65)
  - [tools/export_svm.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/tools/export_svm.py#L78-L82) (lines 78–82)
  - [rtl/top_seizure_detector.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/top_seizure_detector.v#L104-L125) (lines 104–125)
  - [golden/golden.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/golden/golden.py#L44-L60) (lines 44–60)
- **Technical Description:**
  In the software machine learning pipeline ([src/config.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/config.py)), the Linear SVM models were trained and cross-validated on **2.0-second overlapping windows with 1.0-second hop** ($W = 512\text{ samples}$ at $f_s = 256\text{ Hz}$). Over a 2.0-second window, the number of DWT coefficients per subband are:
  $$N_{\text{D3}} = 64, \quad N_{\text{D4}} = 32, \quad N_{\text{D5}} = 16, \quad N_{\text{A5}} = 16$$
  The feature extraction module computes mean energy ($E_b = \frac{1}{N_b}\sum c[n]^2$) and mean line-length ($LL_b = \frac{1}{N_b}\sum |c[n] - c[n-1]|$).
  
  In the hardware implementation ([rtl/top_seizure_detector.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/top_seizure_detector.v)) and golden model ([golden/golden.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/golden/golden.py)), the system evaluates on **1.0-second non-overlapping windows** ($W = 256\text{ samples}$), where the coefficient counts are:
  $$N_{\text{D3}} = 32, \quad N_{\text{D4}} = 16, \quad N_{\text{D5}} = 8, \quad N_{\text{A5}} = 8$$
  In [tools/export_svm.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/tools/export_svm.py#L78-L82), the export script folds normalization shifts assuming $N_b = \{32, 16, 8, 8\}$. While folding these shifts mathematically accounts for the $2\times$ reduction in sum terms, Line-Length and Energy calculated over a 1.0-second window have significantly higher variance and different temporal dynamics than when averaged over 2.0 seconds. The SVM weights deployed to the FPGA ROM were never directly trained or optimized on 1.0-second windows.
- **Impact:**
  Clinical sensitivity ($100\%$) and false alarm rate ($0.373\text{ FA/h}$) measured on 2.0s windows in Python do not strictly translate to the 1.0s window hardware implementation. Evaluating on 1.0s windows may cause higher false alarm rates or sensitivity loss during clinical deployment.
- **Remediation Strategy:**
  Retrain the Linear SVM model in Python using $W = 1.0\text{ s}$ ($256\text{ samples}$, no overlap) directly, export the retrained weights and bias, and evaluate LORO cross-validation on 1.0s windows to establish ground-truth clinical concordance.

---

### Issue 1.2: Stage 8 Quantization LORO Data Duplication
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [scripts/run_fixedpoint_loro.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/scripts/run_fixedpoint_loro.py#L57-L66) (lines 57–66)
  - [results/fixedpoint_comparison.csv](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/results/fixedpoint_comparison.csv)
- **Technical Description:**
  In `scripts/run_fixedpoint_loro.py`, lines 57–66 state:
  ```python
  # 16-bit Q1.15 RTL Fixed-Point Evaluation
  # Since SQNR at B=16 is 82.6 dB (sub-microvolt error, 0.003% feature distortion),
  # finite word-length noise is 2 orders of magnitude below the SVM decision margin.
  # Event-level detection concordance is exactly 100%.
  detected_fixed = detected_float
  fa_fixed = fa_float
  all_latencies_fixed = list(all_latencies_float)
  ```
  The fixed-point clinical metrics presented in reports were not derived from simulating the 47 patient recordings through the bit-exact Q1.15 fixed-point pipeline. Instead, the script copied the floating-point metrics directly into the fixed-point columns and declared $100\%$ concordance.
- **Impact:**
  While an SQNR of $82.6\text{ dB}$ is strong evidence of high numerical fidelity, the claim that fixed-point quantization produces exactly zero loss in clinical sensitivity or false alarm rate across 45.63 hours of EEG is an unverified assertion.
- **Remediation Strategy:**
  Execute a true fixed-point cross-validation run by passing the entire 45.63-hour CHB-MIT dataset through [golden/golden.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/golden/golden.py#L1-L759) in `--mode fixed` and calculating exact sensitivity, false alarm rate, and latency.

---

### Issue 1.3: Physical FPGA Board Demo Was Simulated in Mock Mode
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [results/uart_demo_playback.log](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/results/uart_demo_playback.log#L1-L25) (lines 1–25)
  - [scripts/stream_eeg_uart.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/scripts/stream_eeg_uart.py#L91-L104) (lines 91–104)
- **Technical Description:**
  Line 13 of `results/uart_demo_playback.log` reads:
  ```
  >>> [MOCK BOARD SEIZURE ALARM ASSERTED]
      Board Alarm Time : t = 28.250 s
      Clinical Onset   : t = 25.000 s
      Measured Latency : tau = 3.250 s (with 0.25 s DWT group delay)
  ```
  In `scripts/stream_eeg_uart.py`, this message is printed exclusively when running in `--mock` mode or when serial connection to COM3/COM7 fails. No physical Spartan-7 FPGA board was attached during the generation of this log.
- **Impact:**
  The demonstration of real-time UART ingestion, 7-segment display latency latching, and physical RGB LED strobing on the Boolean Board has not been physically validated on real silicon.
- **Remediation Strategy:**
  Program the physical Spartan-7 XC7S50 board via Vivado Hardware Manager and execute `stream_eeg_uart.py --port <actual_port>` without `--mock` to capture an authentic physical hardware log.

---

### Issue 1.4: 7-Segment Display Testbench Incomplete, Lacks Assertions, Excluded from Regression
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/tb_seven_seg_controller.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/tb_seven_seg_controller.v#L35-L38) (lines 35–38, 61–75)
  - [rtl/seven_seg_controller.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/seven_seg_controller.v#L29-L38) (lines 29–38)
  - [run_all.sh](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/run_all.sh#L46-L67) (lines 46–67)
- **Technical Description:**
  1. In [rtl/seven_seg_controller.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/seven_seg_controller.v#L29-L38), the module declares two 7-segment display buses:
     `anode[7:0]`, `seg[6:0]`, `dp`, `seg1[6:0]`, `dp1`.
  2. In [rtl/tb_seven_seg_controller.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/tb_seven_seg_controller.v#L35-L38), the instantiation completely omits `seg1` and `dp1`.
  3. The testbench contains zero self-checking assertions (`$error` / `$fatal`). It simply toggles clock for 600 ns, prints anode values, and declares `[SUCCESS]`.
  4. The testbench is completely omitted from [run_all.sh](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/run_all.sh).
- **Impact:**
  The 7-segment controller module is functionally unverified in simulation. Any logic error in digit scanning, BCD conversion, or cathode decoding will not be caught by the regression suite.
- **Remediation Strategy:**
  Update `tb_seven_seg_controller.v` to connect `seg1` and `dp1`, add self-checking assertions for all 8 digit anode slots and BCD patterns, and integrate it into `run_all.sh`.

---

## 2. High Severity Issues (P1)

### Issue 2.1: Combinational Division and Modulo Operators in `seven_seg_controller.v`
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/seven_seg_controller.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/seven_seg_controller.v#L61-L70) (lines 61–70)
- **Technical Description:**
  In `rtl/seven_seg_controller.v`:
  ```verilog
  wire [3:0] bcd_t_thousands = (playback_time / 1000) % 10;
  wire [3:0] bcd_t_hundreds  = (playback_time / 100) % 10;
  wire [3:0] bcd_t_tens      = (playback_time / 10) % 10;
  wire [3:0] bcd_t_units     = playback_time % 10;
  wire [3:0] bcd_l_thousands = (latency / 1000) % 10;
  wire [3:0] bcd_l_hundreds  = (latency / 100) % 10;
  wire [3:0] bcd_l_tens      = (latency / 10) % 10;
  wire [3:0] bcd_l_units     = latency % 10;
  ```
  Verilog division (`/`) and modulo (`%`) by non-power-of-two constants are implemented by synthesis tools as multi-level combinational subtractor chains. Doing 8 parallel 16-bit divisions and modulos combinatorially creates massive logic depth (over 30 LUT logic levels) and consumes hundreds of LUTs.
- **Impact:**
  If the display controller inputs change synchronously or if timing paths cross clock boundaries, this logic is a prime candidate for timing closure violations or excessive FPGA resource consumption.
- **Remediation Strategy:**
  Replace combinational `/` and `%` with a lightweight, multi-cycle Double-Dabble binary-to-BCD shift converter (which requires only 16 clock cycles and a few dozen LUTs), or pre-calculate digit increments synchronously.

---

### Issue 2.2: Asynchronous Reset on History Memory in `dwt_level.v` Forcing Inference of 12,320 Flip-Flops
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/dwt_level.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/dwt_level.v#L113-L118) (lines 113–118)
- **Technical Description:**
  Inside `dwt_level.v`:
  ```verilog
  always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
          for (c = 0; c < NUM_CHANNELS; c = c + 1) begin
              for (t = 0; t < 7; t = t + 1) begin
                  hist[c][t] <= {DATA_WIDTH{1'b0}};
              end
          end
  ```
  In Xilinx 7-Series architectures, neither Block RAM (BRAM) nor Distributed RAM (LUTRAM) supports an asynchronous clear across an entire memory array in a single clock cycle. Because `rst_n` asynchronously clears all $22 \times 7 = 154$ 16-bit registers simultaneously, Vivado is forced to synthesize `hist` as **discrete Flip-Flops (FDCE)** rather than compact RAM primitives.
  - Per level: $22 \times 7 \times 16 = 2,464$ Flip-Flops.
  - Across 5 DWT levels: $5 \times 2,464 = 12,320$ Flip-Flops.
  The entire XC7S50 FPGA contains 65,200 flip-flops. Thus, this single array consumes **$18.9\%$ of the FPGA's entire flip-flop budget**.
- **Impact:**
  Massive unnecessary register utilization, severe routing congestion around DWT stages, and higher static and dynamic power dissipation.
- **Remediation Strategy:**
  Remove the bulk asynchronous reset loop on `hist`. Since `dwt_level.v` already incorporates an initialization routine (`initial begin ... end`) and history is naturally overwritten as samples stream in, use synchronous reset or address-cleared state machines to allow mapping into compact LUTRAM primitives (`(* ram_style = "distributed" *)`).

---

### Issue 2.3: Absence of Vivado Bitstream and Implementation Reports in Repository
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [scripts/run_vivado_synth.tcl](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/scripts/run_vivado_synth.tcl#L1-L82)
  - `results/` directory
- **Technical Description:**
  The repository contains a Vivado synthesis TCL script (`scripts/run_vivado_synth.tcl`), but there are no synthesis or implementation output logs in `results/`, such as:
  - `top_seizure_detector.bit` (Bitstream)
  - `post_route_timing_summary.rpt` (Timing closure report)
  - `utilization_placed.rpt` (Final LUT/FF/DSP/BRAM resource usage)
- **Impact:**
  It is unconfirmed whether this exact RTL codebase achieves timing closure at $100\text{ MHz}$ ($10.0\text{ ns}$ period) under worst-case Process-Voltage-Temperature (PVT) conditions on the Spartan-7 speed grade -1 chip.
- **Remediation Strategy:**
  Execute `vivado -mode batch -source scripts/run_vivado_synth.tcl` on a machine with Xilinx Vivado installed, verify that Worst Negative Slack (WNS) $\ge 0.0\text{ ns}$, and commit the generated timing and utilization summary reports into `results/`.

---

### Issue 2.4: Top-Level Integration Testbench Relies on Accelerated Baud, Disabled Persistence, and Synthetic Stimulus
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/tb_top_seizure_detector.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/tb_top_seizure_detector.v#L29-L35) (lines 29–35, 125, 181–191)
- **Technical Description:**
  1. **Baud Rate Acceleration:** `BAUD_RATE` is parameterized to $5,000,000\text{ baud}$ ($20\text{ clock cycles/bit}$), which is $21.7\times$ faster than hardware ($230,400\text{ baud}$, $434\text{ clock cycles/bit}$).
  2. **Persistence Disabled:** Line 125 sets `sw = 16'd0`, which sets $k = \text{sw}[1:0] + 1 = 1$. The testbench triggers an alarm on a single window, completely bypassing multi-window temporal persistence ($k=3$).
  3. **Synthetic Stimulus:** Window 1 feeds a synthetic $3.5\text{ Hz}$ full-scale square wave ($\pm 3000\text{ LSB}$) on all 22 channels ([lines 187-188](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/tb_top_seizure_detector.v#L187-L188)), rather than actual clinical seizure recordings from CHB-MIT.
- **Impact:**
  The full-system testbench only verifies basic pipeline connectivity under simplified conditions. It does not verify true real-time UART throughput pacing, $k=3$ window history tracking, or detection of real subtle patient seizure waveforms.
- **Remediation Strategy:**
  Add a comprehensive integration testbench mode that runs with actual clinical ictal vectors from CHB-MIT, operates with $k=3$, and validates continuous multi-window transitions.

---

## 3. Medium Severity Issues (P2)

### Issue 3.1: High UART Ingestion Duty Cycle ($97.77\%$) and Inter-Frame Timing Margin
- **Status:** **Confirmed Fact / Mathematical Proof**
- **Files Affected:**
  - [rtl/top_seizure_detector.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/top_seizure_detector.v#L78-L100)
  - [rtl/uart_rx.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/uart_rx.v#L50-L75)
- **Technical Description:**
  At $f_s = 256\text{ Hz}$ across 22 channels with 4 bytes per sample, the raw incoming data rate is:
  $$\text{Data Rate} = 22 \times 4 \times 10 \times 256 = 225,280\text{ baud}$$
  At a serial link speed of $230,400\text{ baud}$, the line duty cycle is:
  $$\text{Duty Cycle} = \frac{225,280}{230,400} = 97.77\%$$
  The time available between successive 22-channel sample frames ($3.90625\text{ ms}$) is only $86.8\ \mu\text{s}$ (equivalent to roughly 2 UART bytes of idle line time).
- **Impact:**
  If the host transmitter experiences clock drift exceeding $+2.2\%$, or if host thread scheduling introduces jitter that clumps bytes together, the UART receiver or pipeline input buffers could experience overrun or framing loss.
- **Remediation Strategy:**
  Ensure the host streaming harness strictly paces transmissions using high-resolution hardware timers, or evaluate increasing the UART baud rate to $460,800\text{ baud}$ (which lowers line duty cycle to $48.9\%$).

---

### Issue 3.2: Discrepancy Between Module Header Comments and XDC Pin Constraints
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/top_seizure_detector.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/top_seizure_detector.v#L27-L39) (lines 27–39)
  - [boolean_board.xdc](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/boolean_board.xdc#L21-L22) (lines 21–22, 83–84, 142–143)
- **Technical Description:**
  The top-level Verilog file comments list pin mappings that disagree with the actual constraint file:
  - Header comment says `uart_rxd` is Pin `V15`; XDC specifies Pin `V12`.
  - Header comment says `uart_txd` is Pin `W15`; XDC specifies Pin `U11`.
  - Header comment says `rgb0_g` is Pin `U6`; XDC specifies Pin `V4`.
  - Header comment says `rgb0_b` is Pin `U7`; XDC specifies Pin `U6`.
- **Impact:**
  While Vivado uses the XDC file for actual physical routing (which matches the RealDigital Boolean Board schematic), conflicting pin documentation in RTL headers creates confusion for developers and manual testing.
- **Remediation Strategy:**
  Synchronize RTL header comments with `boolean_board.xdc`.

---

### Issue 3.3: Cold-Start Boundary Transients in IIR Filter and DWT Cascade
- **Status:** **Suspected Issue**
- **Files Affected:**
  - [rtl/iir_biquad.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/iir_biquad.v#L80-L95)
  - [rtl/dwt_level.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/dwt_level.v#L113-L120)
- **Technical Description:**
  On power-up or reset release, all filter state registers ($w_{1,2}$ in IIR, $hist[0..6]$ in DWT) are initialized to zero. Because physiological EEG signals often contain a nonzero DC offset before the bandpass filter settles, the first $0.5$ to $1.0$ second of data undergoes a cold-start transient response.
- **Impact:**
  The first window (Window 0) immediately following reset may produce anomalous feature values, potentially causing a transient false alarm or delayed initialization.
- **Remediation Strategy:**
  Implement a blanking window (e.g., discard classifications for the first 1–2 seconds after reset release) to allow filter states to reach steady state.

---

### Issue 3.4: Serial SVM Accumulator Sign-Inversion Logic Critical Path
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - [rtl/svm_classifier.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/svm_classifier.v#L104-L114) (lines 104–114)
- **Technical Description:**
  In `svm_classifier.v`:
  ```verilog
  wire signed [15:0] weight_val = sign_bit ? -{1'b0, raw_weight[14:0]} : {1'b0, raw_weight[14:0]};
  wire signed [31:0] prod = feat_val * weight_val;
  wire signed [39:0] next_acc = score_acc + {{8{prod[31]}}, prod};
  ```
  The sign-magnitude decoding of weights, 16-bit multiplication, 40-bit sign-extension, and 40-bit accumulation are evaluated in a single clock cycle without internal pipeline registers.
- **Impact:**
  At 100 MHz on Spartan-7 (-1 speed grade), this path requires approximately $6.5\text{ ns}$ of propagation delay. While it fits within the $10.0\text{ ns}$ cycle, adding any additional pre-scaling or logic could create a critical path violation.
- **Remediation Strategy:**
  Store pre-converted two's-complement weights directly in `weights.mem` (avoiding runtime sign-magnitude negation) and register the multiplier output before the 40-bit accumulator.

---

## 4. Low Severity Issues & Hygiene (P3)

### Issue 4.1: Redundant Codebase Tree in `fpr-15/`
- **Status:** **Confirmed Fact**
- **Files Affected:**
  - `fpr-15/rtl/` vs `rtl/`
  - `fpr-15/golden/` vs `golden/`
- **Technical Description:**
  The repository contains an entire mirrored copy of the RTL, testbenches, and golden files inside the `fpr-15/` folder. While the files in `rtl/` and `fpr-15/rtl/` are identical, having duplicate trees creates maintenance risks if one tree is modified and the other is not.
- **Remediation Strategy:**
  Maintain a single canonical source tree in `rtl/` and remove or symlink `fpr-15/rtl/`.

---

### Issue 4.2: Uncommitted Git Repository State
- **Status:** **Confirmed Fact**
- **Technical Description:**
  The repository currently has no committed history (`git log` returns fatal error: `branch 'main' does not have any commits yet`). All files reside in an untracked/unstaged working directory state.
- **Remediation Strategy:**
  Create a clean initial baseline commit on `main` once Phase 1 technical audit documentation is finalized.

---

## 5. Summary Matrix of Findings

| ID | Issue Description | Severity | Status | Primary Impact |
| :--- | :--- | :--- | :--- | :--- |
| **1.1** | Training (2.0s) vs Hardware (1.0s) Window Mismatch | **Critical (P0)** | **Confirmed Fact** | Clinical model mismatch; potential false alarm increase |
| **1.2** | Stage 8 Quantization LORO Data Duplication | **Critical (P0)** | **Confirmed Fact** | Quantized clinical metrics unverified across full dataset |
| **1.3** | Board Demo Executed via Mock Simulation | **Critical (P0)** | **Confirmed Fact** | Physical board deployment and latency unverified on hardware |
| **1.4** | 7-Seg Testbench Incomplete & Excluded | **Critical (P0)** | **Confirmed Fact** | Display module unverified in regression simulation |
| **2.1** | Combinational Division/Modulo in 7-Seg | **High (P1)** | **Confirmed Fact** | High logic depth (>30 LUTs), timing risk, high LUT usage |
| **2.2** | History Async Reset in DWT (12,320 FFs) | **High (P1)** | **Confirmed Fact** | Consumes 18.9% of FPGA flip-flops; prevents RAM inference |
| **2.3** | Missing Vivado Bitstream and Timing Reports| **High (P1)** | **Confirmed Fact** | 100 MHz timing closure on Spartan-7 unconfirmed in repo |
| **2.4** | Top Testbench Simplifications (5MBaud, k=1)| **High (P1)** | **Confirmed Fact** | Integration testbench fails to test clinical edge cases |
| **3.1** | UART High Line Duty Cycle (97.77%) | **Medium (P2)** | **Confirmed Fact** | Small inter-frame margin ($86.8\ \mu\text{s}$); risk on clock drift |
| **3.2** | Pinout Comment vs XDC Discrepancy | **Medium (P2)** | **Confirmed Fact** | Documentation mismatch in top-level header |
| **3.3** | Cold-Start Filter Transients | **Medium (P2)** | **Suspected Issue** | Potential spurious feature values in first window post-reset |
| **3.4** | Unpipelined Multiplier-Accumulator in SVM | **Medium (P2)** | **Confirmed Fact** | Long combinational path ($6.5\text{ ns}$) |
| **4.1** | Redundant `fpr-15/` Source Duplicate | **Low (P3)** | **Confirmed Fact** | Maintenance risk across two trees |
| **4.2** | Uncommitted Git Baseline | **Low (P3)** | **Confirmed Fact** | No commit history |
