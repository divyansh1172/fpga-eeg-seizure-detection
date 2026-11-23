# Technical Audit: RTL Module Inventory
**Project:** FPGA-Based Real-Time Multichannel EEG Seizure Detection  
**Target Hardware:** RealDigital Boolean Board (AMD Spartan-7 `xc7s50csga324-1`)  
**Audit Date:** November 2026  

---

## 1. Inventory Summary

The synthesizable hardware design consists of **10 Verilog RTL modules**, 1 master XDC physical constraints file, and 2 memory initialization files (`weights.mem`, `bias.mem`).

| Module Name | File Path | Line Count | Primary Function | Primary Sub-blocks / Dependencies |
|---|---|---|---|---|
| `top_seizure_detector` | `rtl/top_seizure_detector.v` | 457 | Top-level integration, packet framing FSM, pipeline pacing, board I/O | Instantiates all 8 core subsystems |
| `uart_rx` | `rtl/uart_rx.v` | 120 | 230,400-baud UART receiver with glitch rejection and stop-bit framing check | None (leaf cell) |
| `uart_tx` | `rtl/uart_tx.v` | 65 | 230,400-baud UART transmitter for telemetry alert status byte | None (leaf cell) |
| `iir_biquad` | `rtl/iir_biquad.v` | 257 | 22-channel time-multiplexed 4th-order causal Butterworth bandpass filter | None (leaf cell) |
| `dwt_level` | `rtl/dwt_level.v` | 195 | Modular single-level db4 FIR decomposition with per-channel state RAM | None (leaf cell) |
| `dwt_db4` | `rtl/dwt_db4.v` | 233 | 5-level dyadic multiresolution cascade emitting D3, D4, D5, A5 subbands | Instantiates 5 instances of `dwt_level` |
| `feature_accumulator`| `rtl/feature_accumulator.v`| 394 | Ping-pong double-buffered feature extractor (Energy and Line-Length) | None (leaf cell) |
| `svm_classifier` | `rtl/svm_classifier.v` | 75 | 176-cycle serial MAC Linear SVM classifier with 40-bit accumulator | None (leaf cell) |
| `alarm_logic` | `rtl/alarm_logic.v` | 111 | Persistence ($k \in \{1,2,3,5\}$), 30s refractory blanking, latency latch | None (leaf cell) |
| `seven_seg_controller`| `rtl/seven_seg_controller.v`| 166 | Dual 4-digit common-anode multiplexed 7-segment display driver | None (leaf cell) |
| `boolean_board.xdc` | `rtl/boolean_board.xdc` | 119 | Master physical pin and timing constraints for Spartan-7 CSGA324 | Target package pinout |

---

## 2. Comprehensive Module-by-Module Technical Audit

---

### 2.1 `top_seizure_detector`
* **File:** `rtl/top_seizure_detector.v` (Lines 1–457)
* **Purpose:** Serves as the top-level structural wrapper for the Spartan-7 FPGA implementation on the RealDigital Boolean Board. It houses the 2-flop reset synchronizer, the 4-byte UART packet decoder FSM, inter-stage pipeline flush timing, weight ROM instantiation, and board I/O multiplexing.
* **Port Interface:**
  | Port Name | Direction | Width | Description | Pin Mapping |
  |---|---|---|---|---|
  | `clk` | Input | 1 | 100 MHz onboard oscillator clock | Pin F14 |
  | `rst` | Input | 1 | Master asynchronous active-high reset button (BTN0) | Pin J2 |
  | `btn` | Input | 3:1 | Pushbuttons (btn[1]: alarm clear, btn[3:2]: unused) | Pins J5, H2, J1 |
  | `uart_rxd` | Input | 1 | UART serial stream input from PC | Pin V12 |
  | `uart_txd` | Output | 1 | UART serial telemetry output to PC | Pin U11 |
  | `sw` | Input | 16 | Slide switches (sw[1:0] configure persistence threshold $k$) | Pins V2..K1 |
  | `led` | Output | 16 | Discrete LEDs (ch index, persistence progress, alarm strobe) | Pins G1..A4 |
  | `rgb0_r` | Output | 1 | RGB0 Red cathode (flashing seizure alarm indicator) | Pin V6 |
  | `rgb0_g` | Output | 1 | RGB0 Green cathode (solid streaming OK indicator) | Pin V4 |
  | `rgb0_b` | Output | 1 | RGB0 Blue cathode (tied low) | Pin U6 |
  | `anode` | Output | 8 | Active-low 7-segment digit anodes (0..3 right, 4..7 left) | Pins D5..E4 |
  | `seg` | Output | 7 | Active-low segment cathodes A..G for Display 0 (Right) | Pins D7..B5 |
  | `dp` | Output | 1 | Active-low decimal point for Display 0 | Pin A6 |
  | `seg1` | Output | 7 | Active-low segment cathodes A..G for Display 1 (Left) | Pins F4..D1 |
  | `dp1` | Output | 1 | Active-low decimal point for Display 1 | Pin C1 |
* **Internal Architecture:**
  - Reset synchronizer (lines 50–57): 2-stage DFF asserting asynchronously on `rst`, deasserting synchronously.
  - Sequential memory clear pulse `post_rst_clear` (lines 60–70): 1-cycle strobe generated on `rst_n` release.
  - Button synchronizer `btn1_sync` (lines 73–80): 2-stage DFF on `btn[1]`.
  - Packet framing FSM (lines 103–198): 4 states (`PKT_SYNC`, `PKT_CHAN`, `PKT_MSB`, `PKT_LSB`).
  - Pipeline drain timer (lines 203–214): Asserts `hop_sync` exactly 128 clock cycles after the 256th sample of channel 21.
  - Model weight ROM (lines 314–320): `svm_weight_rom[0:175]` initialized from `weights.mem` via `$readmemh`.
  - Strobe divider `strobe_cnt[23:0]` (lines 396–403): Generates $\approx 5.96$ Hz strobe signal on bit 23 ($100\text{ MHz} / 2^{24}$).
  - Watchdog timer `stream_watchdog[26:0]` (lines 415–424): 1.0-second timer maintaining `streaming_ok` green LED.
* **Clocking & Reset:** Synchronous to 100 MHz `clk`. Asynchronous assert, synchronous deassert via `rst_n`.
* **Fixed-Point Representation:** Operates on 16-bit signed integer EEG samples ($Q1.15$), 16-bit signed weights ($Q1.15$), and 32-bit signed bias ($Q30$ scale).
* **Dependencies:** Instantiates `uart_rx`, `iir_biquad`, `dwt_db4`, `feature_accumulator`, `svm_classifier`, `alarm_logic`, `uart_tx`, `seven_seg_controller`.
* **Verification Status:** Verified via `tb_top_seizure_detector.v`. Simulates 2 windows (1 background, 1 synthetic square wave) at accelerated 5 Mbaud.

---

### 2.2 `uart_rx`
* **File:** `rtl/uart_rx.v` (Lines 1–120)
* **Purpose:** Deserializes incoming asynchronous UART byte streams at 230,400 baud from the CP2102N USB-UART bridge. Verifies start-bit center sampling and stop-bit framing.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low synchronous reset.
  - `rxd` (in, 1-bit): Asynchronous serial input.
  - `byte_valid` (out, 1-bit): 1-cycle active-high pulse indicating complete byte reception.
  - `byte_data` (out, 8-bit): Received byte payload.
  - `frame_err` (out, 1-bit): 1-cycle pulse asserted if stop bit is low ($0$).
* **Internal Architecture:**
  - Input synchronizer (lines 38–47): 2-stage flip-flop chain (`rxd_sync1`, `rxd_sync2`).
  - 4-state receiver FSM (lines 27–30): `STATE_IDLE` (0), `STATE_START` (1), `STATE_DATA` (2), `STATE_STOP` (3).
  - Baud divider `clk_count[11:0]`: Counts $0..433$ (`CLKS_PER_BIT - 1`).
  - False start-bit rejection: Samples at cycle 217 (`HALF_BIT`); if `rxd_sync2 == 1'b1`, aborts to `STATE_IDLE`.
  - Data sampling: Samples bits 0..7 sequentially at full bit period (cycle 433).
  - Stop-bit check: In `STATE_STOP`, samples at cycle 433. If high, asserts `byte_valid`; if low, asserts `frame_err` and drops byte.
* **Clocking & Reset:** Pure 100 MHz synchronous datapath with `rst_n`.
* **Fixed-Point Representation:** N/A (byte framing).
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_uart_rx.v`. 5 self-checking tests pass (normal stream, 0xAA payload, dropped byte resync, corrupted stop bit, line glitch rejection).

---

### 2.3 `uart_tx`
* **File:** `rtl/uart_tx.v` (Lines 1–65)
* **Purpose:** Compact 8N1 serial transmitter used to send hardware telemetry status bytes (specifically `0xA5` on seizure alarm trigger) back to the host computer at 230,400 baud.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `tx_start` (in, 1-bit): 1-cycle pulse requesting transmission.
  - `tx_data` (in, 8-bit): Byte to transmit.
  - `tx_busy` (out, 1-bit): High while serializing a frame.
  - `txd` (out, 1-bit): Serial output to host PC (Pin U11).
* **Internal Architecture:**
  - Shift register `shift_reg[9:0]`: Formats standard 10-bit frame `{stop_bit (1'b1), tx_data[7:0], start_bit (1'b0)}`.
  - Divider `clk_cnt[8:0]`: Counts $0..433$ per bit.
  - Idle state: `txd` is held continuously at `1'b1` (Idle-High) when not transmitting, eliminating the permanent line break condition that existed in the original scaffolding.
* **Clocking & Reset:** Pure 100 MHz synchronous datapath with `rst_n`.
* **Fixed-Point Representation:** N/A (byte framing).
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_alarm_logic.v` (Test 5) and `tb_top_seizure_detector.v`. Confirmed to emit `0xA5` and return cleanly to Idle-High without line faults.

---

### 2.4 `iir_biquad`
* **File:** `rtl/iir_biquad.v` (Lines 1–257)
* **Purpose:** Implements a synthesizable 4th-order causal Butterworth bandpass filter (0.5 to 25.0 Hz at $f_s = 256$ Hz), time-multiplexed across 22 channels.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `reset_state` (in, 1-bit): Synchronous clear pulse that initiates sequential zeroing of all channel memories.
  - `sample_valid` (in, 1-bit): 1-cycle input strobe.
  - `ch_in` (in, 5-bit): Channel index ($0..21$).
  - `sample_in` (in, signed 16-bit): Raw EEG input sample ($Q1.15$).
  - `out_valid` (out, 1-bit): 1-cycle output strobe.
  - `ch_out` (out, 5-bit): Channel index matching `sample_out`.
  - `sample_out` (out, signed 16-bit): Filtered output sample ($Q1.15$).
* **Internal Architecture:**
  - Two cascaded Direct Form I sections: Section 0 (lowpass pair), Section 1 (highpass pair).
  - Channel memory: 8 RAM arrays of depth 22 (`s0_mem_x1/x2`, `s0_mem_y1/y2`, `s1_mem_x1/x2`, `s1_mem_y1/y2`). State width is 34 bits ($Q14.20$).
  - State machine (lines 86–91): `S_IDLE`, `S_SEC0_A`, `S_SEC0_B`, `S_SEC1_A`, `S_SEC1_B`, `S_WRITE`.
  - Arithmetic pipelining: Section products are registered in Stage A; subtraction, rounding, and saturation execute in Stage B. Total latency is 5 clock cycles per channel sample.
  - Sequential clear: A dedicated counter `clear_idx` sweeps $0..21$ over 22 cycles upon `reset_state`.
* **Clocking & Reset:** 100 MHz synchronous. RAM writes occur strictly on `posedge clk`.
* **Fixed-Point Representation:**
  - Coefficients: Shift-20 integer scaling ($2^{20} = 1048576$).
  - Feedforward products: 48 bits. Feedback products: 60 bits ($25\text{-bit coeff} \times 34\text{-bit state}$).
  - Feedback scaling: `>>> 20` before subtraction.
  - Rounding: Add $+524288$ ($2^{19}$) before `>>> 20` arithmetic shift.
  - Output saturation: Clamped strictly to $[-32768, 32767]$.
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_iir_biquad.v`. 11,264 samples across 22 channels match `golden/vectors/tb_iir_expected.hex` with **0 LSB error**; channel crosstalk isolation verified (zero bleed into adjacent channels).

---

### 2.5 `dwt_level`
* **File:** `rtl/dwt_level.v` (Lines 1–195)
* **Purpose:** Modular building block for single-level Daubechies-4 (db4) wavelet decomposition. Evaluates an 8-tap lowpass FIR filter ($H$, approximation) and an 8-tap highpass FIR filter ($G$, detail), followed by dyadic downsampling by 2.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `in_valid` (in, 1-bit): Input sample strobe.
  - `ch_in` (in, 5-bit): Channel index ($0..21$).
  - `data_in` (in, signed 16-bit): Input data sample ($Q1.15$).
  - `out_valid` (out, 1-bit): Output strobe (asserted on decimation phase 1).
  - `ch_out` (out, 5-bit): Output channel index.
  - `approx_out` (out, signed 16-bit): Lowpass approximation coefficient ($Q1.15$).
  - `detail_out` (out, signed 16-bit): Highpass detail coefficient ($Q1.15$).
* **Internal Architecture:**
  - Serial MAC datapath: Evaluates taps $0..7$ over 8 consecutive clock cycles using 2 multipliers (`prod_h`, `prod_g`), completely eliminating the wide 9-input combinational adder tree.
  - Tap buffer `tap_buf[0:7]`: Assembled from incoming `data_in` and 7-sample channel history `hist[ch_in][0:6]`.
  - Decimation phase register `phase_ram[21:0]`: Tracks individual 1-bit decimation state per channel. Toggles on every sample arrival. Computation executes only on phase 1.
  - Accumulators `acc_h`, `acc_g`: 36 bits signed ($32\text{-bit product} + 4\text{ guard bits}$).
  - Rounding & Saturation: Adds $+16384$ before `>>> 15`; `sat16` clamps to $[-32768, 32767]$.
* **Clocking & Reset:** 100 MHz synchronous. Note: `hist` array has an asynchronous reset loop over $22 \times 7$ entries (lines 114–118).
* **Fixed-Point Representation:** 16-bit signed coefficients ($Q1.15$, scale = 32768). Internal products 32-bit signed, accumulators 36-bit signed, outputs 16-bit signed.
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified implicitly through `tb_dwt_db4.v`.

---

### 2.6 `dwt_db4`
* **File:** `rtl/dwt_db4.v` (Lines 1–233)
* **Purpose:** Implements a 5-level cascaded dyadic filter bank decomposing 22 channels into clinical subbands. Retains D3, D4, D5, and A5, tagging coefficients with channel and subband IDs.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `sample_valid` (in, 1-bit): Input sample strobe from IIR filter.
  - `ch_in` (in, 5-bit): Channel index ($0..21$).
  - `sample_in` (in, signed 16-bit): Bandpass filtered EEG sample.
  - `out_valid` (out, 1-bit): Serialized output coefficient strobe.
  - `ch_out` (out, 5-bit): Channel index of emitted coefficient.
  - `subband_id` (out, 2-bit): Subband tag: `2'd0` $\to$ D3, `2'd1` $\to$ D4, `2'd2` $\to$ D5, `2'd3` $\to$ A5.
  - `coeff_out` (out, signed 16-bit): Wavelet coefficient value ($Q1.15$).
  - `valid_d3`, `valid_d4`, `valid_d5`, `valid_a5` (out, 1-bit): One-hot individual subband strobes.
  - `approx_out`, `detail_out` (out, signed 16-bit): Legacy ports wired to `coeff_out`.
* **Internal Architecture:**
  - Instantiates 5 cascaded `dwt_level` instances (`u_lvl1` to `u_lvl5`).
  - Output serialization queue `queue_mem[0:7]`: 8-entry FIFO (23 bits wide: `{subband_id[1:0], ch_out[4:0], coeff[15:0]}`).
  - Queue pop logic (lines 186–202): Emits one coefficient per cycle while `q_count > 0`.
  - Queue push logic (lines 205–225): Priority enqueueing from Levels 5, 4, 3.
* **Clocking & Reset:** 100 MHz synchronous with active-low `rst_n`.
* **Fixed-Point Representation:** 16-bit signed ($Q1.15$) throughout all levels.
* **Dependencies:** Instantiates 5 copies of `dwt_level`.
* **Verification Status:** Verified via `tb_dwt_db4.v`. 11,264 samples across 22 channels match `golden/vectors/tb_dwt_*_expected.hex` with **0 LSB error**. Verified exact output rates (D3: 32/s, D4: 16/s, D5: 8/s, A5: 8/s per channel) and zero crosstalk.

---

### 2.7 `feature_accumulator`
* **File:** `rtl/feature_accumulator.v` (Lines 1–394)
* **Purpose:** Computes Sub-band Energy ($E = \frac{1}{N_b} \sum c^2$) and Line-Length ($LL = \frac{1}{N_b-1} \sum |c_i - c_{i-1}|$) across 22 channels and 4 subbands over a 1.0-second window. Implements double-buffering (ping-pong) to avoid window-boundary data loss.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `reset_state` (in, 1-bit): Synchronous clear pulse.
  - `coeff_valid` (in, 1-bit): Wavelet coefficient strobe from DWT queue.
  - `channel_id` (in, 5-bit): Channel index ($0..21$).
  - `subband_id` (in, 2-bit): Subband tag ($0..3$).
  - `coeff_in` (in, signed 16-bit): Wavelet coefficient ($Q1.15$).
  - `window_sync` (in, 1-bit): 1.0-second window completion strobe (`hop_sync`).
  - `feat_stream_start` (out, 1-bit): 1-cycle strobe aligned with feature 0.
  - `feat_stream_valid` (out, 1-bit): High during 176-cycle feature streaming burst.
  - `feat_index` (out, 8-bit): Feature index ($0..175$).
  - `feat_data` (out, signed 19-bit): Normalized feature value.
  - `feat_ready` (out, 1-bit): 1-cycle strobe asserted on stream completion.
* **Internal Architecture:**
  - Double buffer: Bank 0 and Bank 1, each consisting of:
    `energy` (88 entries $\times$ 38 bits), `ll` (88 entries $\times$ 26 bits), `prev` (88 entries $\times$ 16 bits), `has_prev` (88 entries $\times$ 1 bit).
  - Explicit attribute `(* ram_style = "distributed" *)` on all 8 arrays.
  - Single write port per bank: Multiplexed between accumulation writes and streaming readout clears.
  - Line-length arithmetic (lines 98–101): 17-bit difference `diff_17` to prevent overflow on `coeff_in = -32768` and `prev = 32767`.
  - Normalization function `normalize_feature` (lines 120–171): Exact bit shifts with round-to-nearest and saturation to $[0, 32767]$.
* **Clocking & Reset:** 100 MHz synchronous. RAM writes occur strictly on `posedge clk`.
* **Fixed-Point Representation:**
  - Energy: 16-bit input squared $\to$ 32-bit unsigned product $\to$ 38-bit accumulator. Shifted by 20/19/18/18 bits with $+2^{\text{shift}-1}$ rounding.
  - Line-Length: 17-bit difference $\to$ 16-bit absolute value $\to$ 26-bit accumulator. Shifted by 5/4/3/3 bits with $+2^{\text{shift}-1}$ rounding.
  - Output: 16-bit integer saturated range $[0, 32767]$ zero-extended to 19 bits.
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_feature_accumulator.v`. 2 full windows (352 features) match `golden/vectors/tb_features_expected.hex` with **0 LSB error**; boundary race stress test (simultaneous `coeff_valid` and `window_sync`) confirmed zero data loss.

---

### 2.8 `svm_classifier`
* **File:** `rtl/svm_classifier.v` (Lines 1–75)
* **Purpose:** 176-cycle serial multiply-accumulate engine executing the Linear SVM decision function:
  $$\text{Score} = b_{\text{fixed}} + \sum_{j=0}^{175} (w_{\text{fixed}}[j] \times \text{feat}[j])$$
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `start` (in, 1-bit): 1-cycle strobe initiating classification (`feat_stream_start`).
  - `feat_data` (in, signed 16-bit): Current feature value ($Q1.15$).
  - `weight_data` (in, signed 16-bit): Current weight from ROM ($Q1.15$).
  - `bias_data` (in, signed 32-bit): 32-bit folded bias constant.
  - `done` (out, 1-bit): 1-cycle active-high completion pulse.
  - `decision` (out, 1-bit): Binary classification ($1$: seizure, $0$: non-seizure).
  - `score` (out, signed 40-bit): Final dot-product accumulator score.
* **Internal Architecture:**
  - Multiplier: $16 \times 16 \to 32$-bit signed product (`prod`).
  - Accumulator `accum[39:0]`: Initialized to `bias_ext + prod_ext` on `start`, accumulating `prod_ext` for the remaining 175 cycles.
  - Decision: Registered on cycle 176 as `(accum + prod_ext) > 0`.
  - Latency: Exactly 176 clock cycles ($1.76\,\mu\text{s}$ at 100 MHz).
* **Clocking & Reset:** 100 MHz synchronous with active-low `rst_n`.
* **Fixed-Point Representation:** 16-bit signed feature $\times$ 16-bit signed weight $\implies$ 32-bit signed product; 32-bit signed bias sign-extended to 40 bits; 40-bit signed accumulator.
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_svm_classifier.v`. 60 windows (10,560 features) evaluated against `golden/vectors/tb_svm_scores_expected.hex` and `tb_decisions_expected.hex`: **100.00% decision agreement** and **0 LSB score error**.

---

### 2.9 `alarm_logic`
* **File:** `rtl/alarm_logic.v` (Lines 1–111)
* **Purpose:** Temporal post-processing FSM. Applies $k$-consecutive window persistence filtering, 30-second refractory period blanking, detection timestamp latching, manual button clearing, and UART telemetry strobe triggering.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `k_sel` (in, 2-bit): Persistence select switches `sw[1:0]`.
  - `btn_clear` (in, 1-bit): Synchronized clear button signal (`btn1_sync`).
  - `svm_done` (in, 1-bit): Strobe from SVM classifier.
  - `svm_decision` (in, 1-bit): Window decision ($1$: seizure, $0$: background).
  - `sec_tick` (in, 1-bit): 1.0-second pulse from `hop_sync`.
  - `playback_seconds` (in, 16-bit): Real-time playback timer.
  - `alarm_pulse` (out, 1-bit): 1-cycle strobe on initial alarm trigger.
  - `alarm_latched` (out, 1-bit): High while alarm is active until cleared.
  - `alarm_count` (out, 8-bit): Cumulative count of distinct seizure events.
  - `consec_count` (out, 3-bit): Real-time count of consecutive positive windows.
  - `refractory_active` (out, 1-bit): High while refractory timer $> 0$.
  - `refractory_timer` (out, 6-bit): Countdown timer ($30..0$ seconds).
  - `latched_latency` (out, 16-bit): Playback second of detection trigger.
  - `tx_trigger` (out, 1-bit): 1-cycle strobe triggering telemetry UART transmission.
* **Internal Architecture:**
  - Edge detector on `btn_clear`: Generates `btn_rise = btn_clear && !btn_prev`.
  - Persistence threshold decoder: `00` $\to 1$, `01` $\to 2$, `10` $\to 3$, `11` $\to 5$.
  - Refractory countdown: Decrements `refractory_timer` on `sec_tick` when $> 0$.
  - Clear behavior: `btn_rise` clears `alarm_latched` and `consec_count`, but preserves `refractory_timer`.
* **Clocking & Reset:** 100 MHz synchronous with active-low `rst_n`.
* **Fixed-Point Representation:** N/A (temporal FSM).
* **Dependencies:** None (leaf cell).
* **Verification Status:** Verified via `tb_alarm_logic.v`. Persistence thresholds ($k=1,2,3,5$), 30s refractory blanking, button clearing, and UART telemetry trigger verified.

---

### 2.10 `seven_seg_controller`
* **File:** `rtl/seven_seg_controller.v` (Lines 1–166)
* **Purpose:** Time-multiplexed controller for the dual 4-digit common-anode 7-segment displays on the Boolean Board. Displays elapsed streaming time on Display 1 and detection status / latency on Display 0.
* **Port Interface:**
  - `clk` (in, 1-bit): 100 MHz clock.
  - `rst_n` (in, 1-bit): Active-low reset.
  - `playback_time` (in, 16-bit): Elapsed streaming time in seconds.
  - `latency` (in, 16-bit): Latched detection timestamp in seconds.
  - `alarm_active` (in, 1-bit): 1 if seizure alarm is latched.
  - `alarm_count` (in, 8-bit): Total alarm count.
  - `anode` (out, 8-bit): Active-low digit enables (anodes 0..3 right, 4..7 left).
  - `seg` (out, 7-bit): Active-low cathodes A..G for Display 0.
  - `dp` (out, 1-bit): Active-low decimal point for Display 0.
  - `seg1` (out, 7-bit): Active-low cathodes A..G for Display 1.
  - `dp1` (out, 1-bit): Active-low decimal point for Display 1.
* **Internal Architecture:**
  - Refresh divider `clk_div[16:0]`: Counts $0..99{,}999$ cycles to generate a 1.0 kHz scanning tick (125 Hz per digit).
  - Scanner `digit_idx[2:0]`: Rotates $0..7$ across all 8 display slots.
  - BCD Decoders (lines 61–70):
    Combinational division and modulo by 1000, 100, 10 for `playback_time` and `latency`.
  - Segment encoder `encode_char` (lines 74–97): Maps 0..9 and custom glyphs (`I`=10, `d`=11, `L`=12, `E`=13, `S`=14, `-`=15).
* **Clocking & Reset:** 100 MHz synchronous with active-low `rst_n`.
* **Fixed-Point Representation:** N/A (display driver).
* **Dependencies:** None (leaf cell).
* **Verification Status:** Partially simulated in `tb_seven_seg_controller.v`. **Warning:** `tb_seven_seg_controller.v` is not self-checking (no automated assertions), does not connect `seg1`/`dp1`, and is omitted from `run_all.sh`.
