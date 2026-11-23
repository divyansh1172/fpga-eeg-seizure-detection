# Golden Reference Model: Multichannel Real-Time EEG Seizure Detector

**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad  
**Hardware Target:** RealDigital Boolean Board (AMD Spartan-7 XC7S50, 100 MHz)  
**Authors:** Antigravity Agent & Team 15  

---

## 1. Overview

The `golden/` package provides the bit-accurate mathematical reference model for the real-time multichannel FPGA seizure detection pipeline. It implements both:
1. **64-bit Floating-Point Reference (`--mode float`):** High-precision double-precision software implementation using standard NumPy and SciPy.
2. **Bit-Accurate Fixed-Point RTL Model (`--mode fixed`):** Integer model matching the exact register bit-widths, saturation bounds, and truncation/shift arithmetic designed for synthesizable Verilog RTL.

Both models process an identical 22-channel round-robin interleaved stream at 256 Hz, allowing direct cycle-by-cycle and window-by-window verification of hardware correctness, SQNR, and clinical event detection parity.

---

## 2. Architecture & Data Flow

```
Interleaved int16 Stream (22 ch, 256 Hz)
               │
               ▼
┌────────────────────────────────────────┐
│ Stage 1: Causal Butterworth Bandpass   │ (0.5 - 25 Hz, 4th-order, 2 DF1 biquads)
│          Per-Channel Q20 RAM State     │ Section 0 (LP) + Section 1 (HP)
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Stage 2: 5-Level Dyadic db4 DWT Cascade│ 8-tap decomposition filters (h, g)
│          Per-Channel Shift Regs & Phase│ Retains D3 (32/s), D4 (16/s), D5 (8/s), A5 (8/s)
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Stage 3: Window Feature Accumulator    │ 1.0 s non-overlapping window (256 frames)
│          176 Features (Energy & LL)    │ 38-bit Energy Acc + 26-bit Line-Length Acc
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Stage 4: Linear SVM Classifier         │ Offline folded weights (16-bit) & bias (32-bit)
│          176-Cycle Serial MAC Engine   │ 40-bit accumulator: score = bias + sum(w * x)
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ Stage 5: Alarm Logic & Refractory      │ Persistence k in {1, 2, 3, 5} (sw[1:0])
│          30 s Refractory Blanking      │ Clinical seizure alarm & latency measurement
└────────────────────────────────────────┘
```

### Stage Details

1. **Stage 0 – Packet Framing & Pacing:**
   - 22 channels round-robin interleaved: `(ch0, n=0), (ch1, n=0), ... (ch21, n=0), (ch0, n=1)...`
   - UART framing: 230,400 baud, 8N1 (434 system clock cycles per bit at 100 MHz).
   - Packet format: 4 bytes: `0xAA` (Sync), `ch_id` (0..21), `MSB`, `LSB` (16-bit signed, big-endian).

2. **Stage 1 – IIR Bandpass Filter:**
   - 4th-order Butterworth bandpass (0.5 to 25.0 Hz at $f_s = 256$ Hz).
   - Cascade of two 2nd-order Direct Form I biquad sections (Section 0: Lowpass pair, Section 1: Highpass pair).
   - Fixed-point arithmetic: shift-20 coefficients, Q20 internal state registers with guard bits to eliminate truncation noise and DC amplification.
   - Per-channel state memory: 22 entries.

3. **Stage 2 – Multi-Level Daubechies-4 (db4) DWT:**
   - Standard 8-tap decomposition filters: lowpass `dec_lo` ($h$) and highpass `dec_hi` ($g$).
   - 5-level dyadic cascade:
     - Level 1: 128 coefficients ($A_1, D_1$)
     - Level 2: 64 coefficients ($A_2, D_2$)
     - Level 3: 32 coefficients ($A_3, D_3$) $\to$ **retains $D_3$ (32 coeffs/s)**
     - Level 4: 16 coefficients ($A_4, D_4$) $\to$ **retains $D_4$ (16 coeffs/s)**
     - Level 5: 8 coefficients ($A_5, D_5$) $\to$ **retains $D_5$ (8 coeffs/s) and $A_5$ (8 coeffs/s)**
   - Per-channel decimation phase (1 bit per level per channel) and 8-sample tap buffer per level per channel.

4. **Stage 3 – Feature Accumulation:**
   - Window size: 1.0 second non-overlapping (256 samples per channel).
   - Feature count: 22 channels $\times$ 4 subbands $\times$ 2 features (Energy, Line-Length) = **176 features**.
   - Sub-band Energy: $E = \frac{1}{N_b} \sum c_i^2$ (38-bit accumulator, normalized via wire-shift).
   - Sub-band Line-Length: $LL = \frac{1}{N_b-1} \sum |c_i - c_{i-1}|$ (26-bit accumulator, normalized via wire-shift).

5. **Stage 4 – Linear SVM Inference:**
   - Offline parameter folding: folded effective weights $w_{\text{eff}} = w / (\sigma \cdot S)$ and bias $b_{\text{eff}} = b - \sum (w \mu / \sigma)$.
   - Quantized into 16-bit signed weights ($w_{\text{fixed}} \in [-32768, 32767]$) and 32-bit signed bias ($b_{\text{fixed}}$).
   - 176-cycle serial multiply-accumulate with 40-bit accumulator matching `svm_classifier.v`.

6. **Stage 5 – Alarm & Refractory Post-Processing:**
   - Selectable persistence $k \in \{1, 2, 3, 5\}$.
   - Requires $k$ consecutive positive windows to assert seizure alarm.
   - 30-second refractory timer blocks re-triggering during post-ictal or continued seizure activity.

---

## 3. How to Run

### Basic Execution (Both Float and Fixed-Point with Comparison Report)
```bash
python3 golden/golden.py --mode both --duration 60.0 --onset 30.0 --dump-vectors --k 3
```

### Options
| Argument | Type | Default | Description |
|---|---|---|---|
| `--mode` | string | `both` | Execution mode: `float`, `fixed`, or `both` |
| `--duration` | float | `60.0` | Total duration of synthetic EEG stream in seconds |
| `--onset` | float | `30.0` | Clinical seizure onset timestamp in seconds |
| `--subject` | string | `chb01` | Patient model to load (`chb01`, `chb02`, `chb03`) |
| `--k` | int | `3` | Persistence parameter $k \in \{1, 2, 3, 5\}$ |
| `--dump-vectors` | flag | `False` | Export `.hex` / `.mem` test vectors into `golden/vectors/` |

---

## 4. Test Vectors Generated (`golden/vectors/`)

When `--dump-vectors` is enabled, the following test vector files are generated for Verilog testbenches:

| File | Target RTL Testbench | Description | Format |
|---|---|---|---|
| `tb_uart_rx_stimulus.hex` | `tb_uart_rx.v` | Raw UART byte stream (4 bytes/sample: `0xAA`, `ch`, MSB, LSB) | 2-char hex (8-bit) |
| `tb_iir_input.hex` | `tb_iir_biquad.v` | 22-channel interleaved raw 16-bit input samples | 4-char hex (16-bit) |
| `tb_iir_expected.hex` | `tb_iir_biquad.v` | Expected filtered 16-bit samples | 4-char hex (16-bit) |
| `tb_dwt_input.hex` | `tb_dwt_db4.v` | Filtered samples input to DWT | 4-char hex (16-bit) |
| `tb_dwt_d3_expected.hex` | `tb_dwt_db4.v` | Expected Level 3 detail coefficients ($D_3$, 32/s/ch) | 4-char hex (16-bit) |
| `tb_dwt_d4_expected.hex` | `tb_dwt_db4.v` | Expected Level 4 detail coefficients ($D_4$, 16/s/ch) | 4-char hex (16-bit) |
| `tb_dwt_d5_expected.hex` | `tb_dwt_db4.v` | Expected Level 5 detail coefficients ($D_5$, 8/s/ch) | 4-char hex (16-bit) |
| `tb_dwt_a5_expected.hex` | `tb_dwt_db4.v` | Expected Level 5 approx coefficients ($A_5$, 8/s/ch) | 4-char hex (16-bit) |
| `tb_features_expected.hex`| `tb_feature_accumulator.v` | Expected 176 features per 1-second window | 4-char hex (16-bit) |
| `weights.mem` | `top_seizure_detector.v` | 176 offline-folded 16-bit signed SVM weights | 4-char hex (16-bit) |
| `bias.mem` | `top_seizure_detector.v` | Offline-folded 32-bit signed SVM bias | 8-char hex (32-bit) |
| `tb_svm_scores_expected.hex` | `tb_svm_classifier.v` | Expected 40-bit accumulated decision scores | 10-char hex (40-bit) |
| `tb_decisions_expected.hex` | `tb_svm_classifier.v` | Expected 1-bit binary decisions ($1=\text{seizure}$) | 1-bit text |
| `tb_alarms_expected.hex` | `tb_alarm_logic.v` | Expected 1-bit alarm trigger pulses | 1-bit text |

---

## 5. Measured Verification & Fidelity Results

Benchmark execution on 60-second 22-channel continuous stream (onset scheduled at $t = 30.0$ s):

```text
================================================================================
 VERIFICATION & QUANTIZATION FIDELITY REPORT (Float vs. Fixed-Point)
================================================================================
Stage 1 (IIR Bandpass 0.5-25 Hz):
  Full-Scale SQNR:      90.67 dB  (Target: >80.0 dB)
  Max Absolute Error:   1.35 LSB  (16-bit signed integer)

Stage 2 & 3 (DWT & Feature Extraction):
  SQNR:                 56.68 dB
  Mean Relative Err:    3.05%

Stage 4 (Linear SVM Inference):
  Decision Agreement:   100.00%   (Target: >=99.9%)
  Mean Score Abs Error: 0.0970
  Seizure Windows:      Float = 30, Fixed = 30

Stage 5 (Alarm Logic: Persistence k=3, 30 s Refractory):
  Float Alarms Fired:   1 at window: [32]
  Fixed Alarms Fired:   1 at window: [32]
  Ground Truth Onset:   t = 30.0 s
  First Alarm Window:   t = 32.0 s
  Detection Latency:    2.0 s     (Target: <= 3.0 s)
================================================================================
>>> GATE VERIFICATION: PASSED (Parity meets course specification) <<<
================================================================================
```
