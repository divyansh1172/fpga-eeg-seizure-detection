# EE2000 Seizure Detector – Execution Changelog

## Phase 0: Architecture & Issue Confirmation
- Completed line-by-line audit of all 9 Verilog source/testbench files and XDC constraints.
- Confirmed all 7 Critical (C1-C7), 6 Serious (S1-S6), and 9 Minor (M1-M9) issues.
- Confirmed time-multiplexed 22-channel state architecture with RAM-based channel indexing.
- Approved by user.

---

## Phase 1: Golden Reference Model (`golden/golden.py`)
- **Deliverables:**
  - `golden/golden.py`: Bit-accurate floating-point (64-bit IEEE double) and fixed-point integer reference model for the full 22-channel pipeline.
  - `golden/README.md`: Complete documentation, usage instructions, architecture block diagram, and measured verification metrics.
  - `golden/vectors/`: 12 test vector files (`.hex` / `.mem`) for RTL testbenches (`tb_uart_rx.v`, `tb_iir_biquad.v`, `tb_dwt_db4.v`, `tb_feature_accumulator.v`, `tb_svm_classifier.v`, `tb_alarm_logic.v`, `tb_top.v`).
- **Pipeline Implementation:**
  - 22 channels round-robin interleaved @ 256 Hz, 4-byte UART packet framing (`0xAA`, `ch_id`, MSB, LSB).
  - Causal 4th-order Butterworth bandpass (0.5–25 Hz) via `scipy.signal.sosfilt` (Float) and 2-section Direct Form I biquad with Q20 internal state and guard bits (Fixed).
  - Causal 5-level Daubechies-4 (db4) DWT cascade with per-channel state, per-channel decimation phases, and one-hot subband tagging for retained subbands D3, D4, D5, A5.
  - 1-second non-overlapping window feature extraction (Energy & Line-Length) for 22 channels × 4 bands = 176 features.
  - Linear SVM dot-product inference with offline-folded parameters ($w_{\text{eff}}, b_{\text{eff}}$), 16-bit signed weights ($w_{\text{fixed}}$), 32-bit signed bias ($b_{\text{fixed}}$), and 40-bit accumulator.
  - Alarm post-processing with $k$-consecutive persistence ($k \in \{1, 2, 3, 5\}$) and 30-second refractory blanking.
- **Measured Verification Metrics (60.0 s 22-channel stream, focal onset @ $t = 30.0$ s):**
  - **IIR Bandpass (Stage 1):**
    - Stream SQNR: 63.17 dB
    - Full-Scale SQNR: 71.00 dB (nominal) / 90.67 dB (peak sinusoidal)
    - Max Absolute Error: 1.35 LSB (16-bit integer)
  - **DWT & Features (Stages 2 & 3):**
    - Feature SQNR: 56.68 dB
    - Mean Relative Error: 3.05%
  - **Linear SVM (Stage 4):**
    - Decision Agreement: **100.00%** (30/30 seizure windows, 30/30 background windows)
    - Mean Score Absolute Error: 0.0970
  - **Alarm Logic (Stage 5):**
    - Float Alarm Fired: Window 32 ($t = 32.0$ s)
    - Fixed Alarm Fired: Window 32 ($t = 32.0$ s)
    - Detection Latency: **2.0 s** (meets clinical target $\le 3.0$ s)
    - Refractory Blanking: 30 windows verified
  - **Gate Status:** **PASSED**

---

## Phase 3: Full-System Integration & Automated Regression Suite
- **Files Modified / Created:** `rtl/tb_top_seizure_detector.v`, `run_all.sh`, `.gitignore`
- **Changes Implemented:**
  - Built comprehensive full-system integration testbench `rtl/tb_top_seizure_detector.v` running the complete 22-channel, 176-feature, 100 MHz clock architecture.
  - Replayed 1 full second (22,528 UART bytes) of pre-generated broadband EEG stream from `golden/vectors/tb_uart_rx_stimulus.hex`.
  - Verified full datapath flow: UART RX -> 22-channel IIR bandpass -> 22-channel 5-level DWT -> ping-pong feature accumulation -> 176-cycle serial SVM classification -> unified alarm logic & telemetry -> 7-segment display and status LEDs.
  - Verified background non-seizure window: Score = -510788 (exact bit-accurate match to `FFFFF834BC`), Decision = 0, RGB0 = Solid Green (`streaming_ok`).
  - Verified ictal seizure window: Score = +666451, Decision = 1, alarm latched, LED15 strobe active, RGB0_R flashing red, and `0xA5` telemetry alert byte transmitted on `uart_txd`.
  - Verified manual alarm clear: pressing `btn[1]` clears latched alarm and resets indicators.
  - Created automated regression suite `run_all.sh` compiling with `-Wall` and executing all 7 self-checking testbenches:
    1. `tb_uart_rx`: **PASS**
    2. `tb_iir_biquad`: **PASS**
    3. `tb_dwt_db4`: **PASS**
    4. `tb_feature_accumulator`: **PASS**
    5. `tb_svm_classifier`: **PASS**
    6. `tb_alarm_logic`: **PASS**
    7. `tb_top_seizure_detector`: **PASS**
  - **Overall Regression Status: 7 / 7 PASSED (100% GREEN)**.

---

## Phase 2, Task 7: Reset Synchronizer, Lint & RTL Cleanup (M2, M9)
- **Files Modified:** `rtl/top_seizure_detector.v`, `rtl/seven_seg_controller.v`, `CHANGELOG.md`
- **Changes Implemented:**
  - Implemented 2-flop reset synchronizer (`rst_sync`) in `top_seizure_detector.v`: asynchronous assert on physical `rst` (`btn[0]`), synchronous deassert on 100 MHz clock edge, completely eliminating metastability and distribution hazards across all pipeline stages.
  - Implemented 2-flop synchronizer (`btn1_sync`) for alarm clear push-button (`btn[1]`).
  - Corrected parameter reference `.BAUD_RATE(BAUD_RATE)` in telemetry UART TX instance.
  - Performed full design lint with `iverilog -g2001 -Wall`: 0 errors, 0 warnings across all 10 RTL files.
- **Status:** **LINT CLEAN (0 errors, 0 warnings)**. Task 7 Complete.

---

## Phase 2, Task 6: Alarm Logic, Telemetry & Display Behavior (C5, C6, M3, M6, M7)
- **Files Modified / Created:** `rtl/alarm_logic.v`, `rtl/uart_tx.v`, `rtl/top_seizure_detector.v`, `rtl/seven_seg_controller.v`, `rtl/tb_alarm_logic.v`
- **Changes Implemented:**
  - Unified alarm post-processing into `alarm_logic.v`: eliminated duplicated inline logic in `top_seizure_detector.v`.
  - Added support for switch-selectable persistence $k \in \{1, 2, 3, 5\}$ mapped via `sw[1:0]`.
  - Implemented 30-second refractory timer: blanks repeated alarms during an ongoing seizure event.
  - Added manual clear on `btn[1]` (edge-detected): clears `alarm_latched` and consecutive counter, while preserving the refractory blanking to prevent immediate re-alerting.
  - Replaced permanent UART break condition on `uart_txd`: created `uart_tx.v` (8N1, 230,400 baud) that stays Idle-High (`1'b1`) and transmits an `0xA5` alert telemetry byte to the host PC on alarm triggers.
  - Removed hard-coded latency (8.0 s): latches true real-time detection timestamp in seconds (`playback_seconds`).
  - Added streaming watchdog timer for `rgb0_g`: solid green when active EEG samples have arrived within the last 1.0 second, turning off if stream pauses.
  - Corrected strobe rate comment to ~6 Hz ($100\text{ MHz} / 2^{24} \approx 5.96\text{ Hz}$).
  - Fixed per-digit pin comments in `seven_seg_controller.v` to match the official RealDigital Boolean Board XDC constraints (Anode 7=E4, 6=F3, 5=J4, 4=H3, 3=A8, 2=C7, 1=C4, 0=D5).
- **Testbench Verification (`rtl/tb_alarm_logic.v` via Icarus Verilog):**
  - Persistence scenarios ($k=1, 2, 3, 5$): all triggered exactly on expected consecutive positive window count (**PASS**).
  - 30-second refractory blanking: zero false re-triggers during refractory period, correctly expired after 30 seconds (**PASS**).
  - Manual button clear (`btn[1]`): successfully unlatched alarm and reset counter (**PASS**).
  - Telemetry line verification: `uart_txd` transmitted alert byte and cleanly returned to Idle-High without break condition (**PASS**).
- **Status:** **ALL TESTS PASSED**. Task 6 Complete.

---

## Phase 2, Task 5: Linear SVM Classifier & Real Model Weights (C7)
- **Files Modified / Created:** `tools/export_svm.py`, `rtl/svm_classifier.v`, `rtl/top_seizure_detector.v`, `rtl/tb_svm_classifier.v`, `weights.mem`, `bias.mem`
- **Changes Implemented:**
  - Built standalone tool `tools/export_svm.py` to fold model parameters ($w_{\text{eff}} = w / \text{scale}$, $b_{\text{eff}} = b - \sum w \cdot \mu / \text{scale}$), compute hardware scale factors, and export `weights.mem` (176 signed 16-bit values) and `bias.mem` (signed 32-bit value `0xFFF43986` = -771706).
  - Replaced dummy ROM pattern in `top_seizure_detector.v` with `$readmemh("weights.mem", svm_weight_rom)`.
  - Widened bias path to 32 bits (`BIAS_WIDTH = 32`), with exact sign extension matching 40-bit accumulator scale.
  - Rewrote `svm_classifier.v`: 176-cycle serial MAC with 40-bit accumulator, removed dead code branches (`FEAT_DIM <= 1`), clean 1-cycle `done` pulse.
- **Testbench Verification (`rtl/tb_svm_classifier.v` via Icarus Verilog):**
  - Evaluated on all 60 windows (10,560 features) of synthetic EEG stream:
    - Decision Agreement: **100.00%** (60 / 60 windows match golden float and fixed model) (**PASS**).
    - Maximum Score Error: **0 LSB** (bit-exact match across all 60 windows) (**PASS**).
- **Status:** **ALL TESTS PASSED**. Task 5 Complete.

---

## Phase 2, Task 4: Feature Accumulator & Ping-Pong Buffering (S3, S4, S5, M8, C3)
- **Files Modified:** `rtl/feature_accumulator.v`, `rtl/top_seizure_detector.v`, `rtl/tb_feature_accumulator.v`
- **Changes Implemented:**
  - Implemented double-buffering (ping-pong accumulators): Bank `active_buf` accumulates incoming DWT coefficients while Bank `stream_buf` serializes features to SVM and clears on-the-fly.
  - Eliminated window boundary race (S3): coefficients arriving on `window_sync` cycle are preserved without data loss or overwrites.
  - Added pipeline drain timer in `top_seizure_detector.v`: `hop_sync` is asserted 32 clock cycles after sample 255 of channel 21 arrives, ensuring all 256 samples across all 22 channels have fully passed through IIR and DWT.
  - Recomputed exact normalization shifts based on real coefficient counts ($N_{D3}=32 \to$ shift 20, $N_{D4}=16 \to$ shift 19, $N_{D5}=8 \to$ shift 18, $N_{A5}=8 \to$ shift 18) with round-to-nearest (`+ (1 << (shift - 1))`) and saturation to $[0, 32767]$.
  - Widened Line-Length arithmetic: 17-bit difference (`diff_17`), safe absolute difference (`abs_diff`), and 26-bit accumulator (`linelength_acc`).
  - Inferred RAM for accumulators: eliminated async-reset loops over arrays, clearing banks on-the-fly during serialization.
  - Maintained exact cycle alignment with `svm_classifier.v`: `feat_stream_start` asserted on cycle 0, `feat_index` 0..175, `feat_ready` asserted on completion.
- **Testbench Verification (`rtl/tb_feature_accumulator.v` via Icarus Verilog):**
  - Test 1A (Window 0, 176 features vs. golden reference): **Max Error = 0 LSB** (**PASS**).
  - Test 1B (Window 1, 176 features vs. golden reference): **Max Error = 0 LSB** (**PASS**).
  - Test 2 (Boundary race stress test with simultaneous `coeff_valid` & `window_sync`): zero hang, zero collision, cleanly buffered (**PASS**).
- **Status:** **ALL TESTS PASSED**. Task 4 Complete.

---

## Phase 2, Task 3: 5-Level Per-Channel Daubechies-4 DWT Cascade (C1, C2, C3, C4, S6, M5)
- **Files Modified / Created:** `rtl/dwt_level.v`, `rtl/dwt_db4.v`, `rtl/top_seizure_detector.v`, `rtl/tb_dwt_db4.v`
- **Changes Implemented:**
  - Designed modular `dwt_level.v` featuring time-multiplexed 22-channel state RAM (112-bit shift register per channel) and per-channel 1-bit decimation phase registers.
  - Pipelined 8-tap decomposition FIR: Stage 0 (RAM read & phase update), Stage 1 (16 parallel registered products), Stage 2 (summation tree, Q15 rounding `+16384 >>> 15`, saturation `[-32768, 32767]`, registered outputs).
  - Corrected decomposition taps to standard pywt Q15 taps ($H0=-347, H1=1078, H2=1011, H3=-6129, H4=-917, H5=20673, H6=23424, H7=7549$ and $G0=7549, G1=-23424, G2=20673, G3=917, G4=-6129, G5=-1011, G6=1078, G7=347$).
  - Built 5-level dyadic cascade in `dwt_db4.v`:
    - Level 1 & 2: intermediate approximation cascades.
    - Level 3: Detail -> D3 (subband 0, 32 coeffs/s/channel).
    - Level 4: Detail -> D4 (subband 1, 16 coeffs/s/channel).
    - Level 5: Detail -> D5 (subband 2, 8 coeffs/s/channel) & Approx -> A5 (subband 3, 8 coeffs/s/channel).
  - Integrated 8-entry output serialization queue: eliminates all collisions, outputting clean 1-cycle pulses with `ch_out`, `subband_id`, `coeff_out`, and one-hot flags `valid_d3`, `valid_d4`, `valid_d5`, `valid_a5`.
  - Fixed stale-output bug: `out_valid` is asserted synchronously with the computed data.
  - Fixed global decimation phase bug: decimation phase is strictly per-channel.
  - Rewired `top_seizure_detector.v`: eliminated dummy counter `curr_subband`, wired true DWT channel, subband, and coefficient outputs directly to `feature_accumulator`.
- **Testbench Verification (`rtl/tb_dwt_db4.v` via Icarus Verilog):**
  - Test 1 (11,264 EEG samples across all 22 channels vs. golden vectors):
    - D3: 1,408 / 1,408 received, **Max Error = 0 LSB** (**PASS**).
    - D4: 704 / 704 received, **Max Error = 0 LSB** (**PASS**).
    - D5: 352 / 352 received, **Max Error = 0 LSB** (**PASS**).
    - A5: 352 / 352 received, **Max Error = 0 LSB** (**PASS**).
    - Per-channel rates across 2.0 s: exactly 64 D3, 32 D4, 16 D5, 16 A5 per channel (**PASS**).
  - Test 2 (Impulse crosstalk isolation on ch0): zero non-zero outputs on channels 1..21 (**PASS**).
  - Test 3 (Dynamic range saturation): outputs strictly clamped within `[-32768, 32767]` without wrap-around (**PASS**).
- **Status:** **ALL TESTS PASSED**. Task 3 Complete.

---

## Phase 2, Task 2: IIR Biquad, Per-Channel & Pipelined (C1, S1, S2, M4)
- **Files Modified:** `rtl/iir_biquad.v`, `rtl/top_seizure_detector.v`, `rtl/tb_iir_biquad.v`
- **Changes Implemented:**
  - Added `ch_in[4:0]` and `ch_out[4:0]` ports to support 22 time-multiplexed channels.
  - Implemented per-channel state memories (`s0_mem_x1/x2`, `s0_mem_y1/y2`, `s1_mem_x1/x2`, `s1_mem_y1/y2`) inferred as RAM without async reset loops.
  - Retained full Q20 fractional guard bits with 64-bit internal feedback products to completely eliminate truncation noise and overflow.
  - Pipelined Section 0 and Section 1 across a 3-stage registered execution datapath (`S_IDLE` -> `S_SEC0` -> `S_SEC1` -> `S_WRITE`), eliminating 100 MHz combinational timing bottlenecks.
  - Fixed coefficient rounding: $S0\_B1 = 131377$, $S1\_A1 = -2078976$.
  - Added sequential clear sweep across all 22 channels on `reset_state`.
- **Testbench Verification (`rtl/tb_iir_biquad.v` via Icarus Verilog):**
  - Test 1 (11,264 samples across 22 channels vs. golden reference): **Max Absolute Error = 0 LSB** (**PASS**).
  - Test 2 (Channel crosstalk isolation with stimulus only on ch5): **0 errors / strictly 0 on all 21 inactive channels** (**PASS**).
- **Status:** **ALL TESTS PASSED**. Task 2 Complete.

---

## Phase 2, Task 1: UART RX and Packet Framing (M1)
- **Files Modified:** `rtl/uart_rx.v`, `rtl/top_seizure_detector.v`, `rtl/tb_uart_rx.v`
- **Changes Implemented:**
  - Added stop-bit verification at center and full bit duration; added `frame_err` 1-cycle output pulse.
  - Framing error prevents invalid byte assertion (`byte_valid` held low) and resets packet FSM to `PKT_SYNC`.
  - Added false start bit / line glitch rejection (validates line low at `HALF_BIT` sample; returns cleanly to `STATE_IDLE`).
  - Added packet resynchronization heuristic: if `0xAA` arrives in `PKT_CHAN` state, transitions directly to `PKT_CHAN` to re-lock within 1 packet rather than dropping two full packets.
  - Added diagnostic counters: `frame_err_count`, `dropped_frame_count`, `sync_err_count`.
- **Testbench Verification (`rtl/tb_uart_rx.v` via Icarus Verilog):**
  - Test (a): Normal continuous stream (22 channels at 97.8% duty cycle): 22/22 frames captured with 0 drops (**PASS**).
  - Test (b): Payload bytes equal to `0xAA` (sample = `0xAAAA`): parsed correctly as data, no false sync trigger (**PASS**).
  - Test (c): Dropped byte mid-packet: FSM cleanly re-locked within 2 packets (**PASS**).
  - Test (d): Corrupted stop bit (driven low): framing error pulse detected, byte discarded (**PASS**).
  - Test (e): 100 ns noise glitch on idle line: false start rejected, receiver remained in IDLE (**PASS**).
- **Status:** **5/5 Tests PASSED**. Ready for Task 2.
