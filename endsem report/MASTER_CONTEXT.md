# EE2000 Final Project: Master Technical Context & Architecture
**Project:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Target Platform:** AMD Spartan-7 XC7S50 (`xc7s50csga324-1`) on RealDigital Boolean Board  
**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad | Team 15  

---

## 1. System High-Level Architecture
The project realizes an ultra-low-power, deterministic, patient-specific seizure detector processing 22 scalp EEG channels in real time. The datapath operates continuously on streaming samples at $f_s = 256\text{ Hz}$ ($3.906\text{ ms}$ per 22-channel frame), executing a five-stage pipelined architecture:

```
[Raw Multichannel EEG (22 Ch @ 256 Hz)]
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 1: Causal IIR Bandpass Preprocessing (0.5–25 Hz)  │
│ Direct Form II Biquad Cascade, zeroed per record        │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 2: 5-Level Dyadic DWT Filter Bank (Daubechies-4) │
│ Streaming convolve + decimate-by-2; D1, D2 discarded     │
│ Retained sub-bands: D3 (16-32 Hz), D4 (8-16 Hz),        │
│                     D5 (4-8 Hz),   A5 (0-4 Hz)          │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 3: Window Feature Accumulation (2.0 s / 1.0 s hop)│
│ Sub-band Energy (E) and Line-Length (LL) per channel    │
│ 22 channels × 4 sub-bands × 2 features = 176 features   │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 4: Linear SVM Classification with Offline Folding │
│ Single time-multiplexed DSP48E1 MAC (176 cycles)        │
│ Evaluates: y = w_eff^T x + b_eff                       │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ Stage 5: Temporal Post-Processing Alarm Logic           │
│ k = 3 consecutive positive windows                      │
│ 30-second refractory blanking period                    │
│ Drives Board LEDs, RGB Status LED, and 7-Segment Display│
└─────────────────────────────────────────────────────────┘
```

---

## 2. Dataset & Signal Processing Protocol
1. **Dataset:** CHB-MIT Scalp EEG Database (PhysioNet). 256 Hz sampling rate, 16-bit analog-to-digital resolution.
2. **Subject Selection (Mechanical Rule):**
   - First subjects in numerical order with $\ge 3$ clinical seizures and the standard 23-channel bipolar montage: `chb01`, `chb02`, `chb03`.
   - 17 total seizures, 45.63 non-seizure control hours across 47 recordings (165,237 total windows).
   - Duplicate `T8-P8` electrode pair is omitted, yielding 22 unique spatial channels.
   - *Montage Inversion Invariance:* Channel 3 (`T7-P7`) and Channel 19 (`P7-T7`) have opposite electrode polarities ($y = -x$). Because Energy ($x^2$) and Line-Length ($|x_n - x_{n-1}|$) are strictly sign-invariant, both channels produce mathematically identical feature trajectories.
3. **Evaluation Protocol:**
   - Strict Leave-One-Record-Out (LORO) patient-specific cross-validation.
   - Window size: $T = 2.0\text{ s}$ (512 samples), hop $h = 1.0\text{ s}$ (256 samples).
   - Training window labeled positive if $\ge 50\%$ overlaps an annotated seizure event.
   - Linear SVM with balanced class weights trained exclusively on training folds; hyperparameters never tuned on test folds.
4. **Scoring Rules:**
   - Seizure detected if an alarm occurs in the window $[t_{\text{onset}} - 2.0\text{ s}, t_{\text{offset}}]$.
   - Refractory period: 30 seconds after any alarm during which subsequent triggers are clustered into the initial event.
   - Latency: $\tau = t_{\text{alarm}} - t_{\text{onset}}$, where $t_{\text{alarm}}$ is the end timestamp of the $k$-th consecutive positive window.

---

## 3. Mathematical Foundations & Hardware Optimizations

### 3.1 Causal Bandpass Preprocessing
A 4th-order Butterworth bandpass filter ($0.5\text{--}25\text{ Hz}$) is implemented as a cascade of two 2nd-order Direct Form II sections (SOS). Filter state is causal and initialized to zero at the start of each file to prevent inter-recording state leakage.

### 3.2 5-Level Dyadic Daubechies-4 (db4) DWT
The 8-tap Daubechies-4 low-pass analysis filter $h[n]$ and high-pass analysis filter $g[n]$ decompose the signal across 5 dyadic octaves:
- Level 1: D1 (64–128 Hz) — Discarded (high-frequency muscle artifact).
- Level 2: D2 (32–64 Hz) — Discarded (saves 20% compute with 0% metric loss).
- Level 3: D3 (16–32 Hz, beta band) — Decimated sub-band length $N_{\text{D3}} = 64$ samples.
- Level 4: D4 (8–16 Hz, alpha/sigma band) — Decimated sub-band length $N_{\text{D4}} = 32$ samples.
- Level 5: D5 (4–8 Hz, theta band) — Decimated sub-band length $N_{\text{D5}} = 16$ samples.
- Level 5: A5 (0–4 Hz, delta band) — Decimated sub-band length $N_{\text{A5}} = 16$ samples.

#### Filter Memory Span vs. Passband Group Delay
- Causal Impulse-Response Support Span:
  $$\text{Span} = (L - 1)(2^J - 1) = (8 - 1)(2^5 - 1) = 7 \times 31 = 217 \text{ samples} \implies 218 \text{ taps} \approx 0.85\text{ s}.$$
- Effective Passband Group Delay: Standard db4 is an extremal-phase (minimum-phase) wavelet with energy concentrated in the initial taps. The effective passband group delay through the 5-level cascade is:
  $$d_{\text{DWT}} \approx 0.20\text{--}0.25\text{ s}.$$
Both the Python streaming pipeline and the Verilog hardware share this identical causal delay.

### 3.3 Offline Weight Folding (Zero DSP Divider / Scaler)
In software, the linear SVM evaluates:
$$f(\mathbf{x}) = \sum_{i=1}^{176} w_i \left( \frac{\bar{x}_i - \mu_i}{\sigma_i} \right) + b$$
where $\bar{x}_i = \frac{1}{S_i} X_i$, with $X_i$ being the raw accumulator sum and $S_i \in \{N_b, N_b-1\}$ being the sub-band sample count.
To eliminate all division and scaling logic on the FPGA, parameters are algebraically folded offline:
$$w_{\text{eff},i} = \frac{w_i}{\sigma_i S_i}$$
$$b_{\text{eff}} = b - \sum_{i=1}^{176} \frac{w_i \mu_i}{\sigma_i}$$
The FPGA evaluates the exact same decision boundary directly from raw accumulator sums:
$$f(\mathbf{X}) = \sum_{i=1}^{176} w_{\text{eff},i} X_i + b_{\text{eff}}$$
This executes in strictly 176 clock cycles ($1.76\ \mu\text{s}$ at 100 MHz) using a single DSP48E1 slice.

### 3.4 Hardware Dynamic-Range Wire-Shift
The Xilinx 7-Series DSP48E1 slice contains a single $25 \times 18$-bit signed multiplier.
- **Line-Length Accumulator:** Accumulates 63 absolute differences of 16-bit values $\implies \lceil \log_2(63) \rceil + 16 = 22\text{ bits}$ (fits natively into the 25-bit port).
- **Energy Accumulator:** In Q1.15 fixed-point, squaring a 16-bit coefficient produces a Q2.30 product scaled by $2^{30}$. Accumulating $N_b \le 64$ squared values yields a 38-bit sum ($\lceil \log_2(64) \rceil + 32 = 38\text{ bits}$).
- **The Wire-Shift Solution (0 LUT Cost):**
  At the accumulator output, drop the 15 fractional LSBs and right-shift by $\log_2(N_b) \in \{6, 5, 4, 4\}$:
  $$X_{\text{E,norm}} = X_{\text{E,raw}}[34 : 15 + \log_2(N_b)]$$
  This normalizes Energy to $\le 19\text{ bits}$ on the exact same numerical scale as Line-Length, fitting directly into the 25-bit DSP48E1 input port in 1 clock cycle and preventing weight underflow in the 16-bit BRAM weight table!

---

## 4. Verified Baseline Results (Mid-Term Benchmark)

| Metric | Proposed DWT + Linear SVM | Replicated Shoeb & Guttag (2010) | Statistical Comparison |
|---|---|---|---|
| **Sensitivity** | **100.0%** (17/17 seizures) | **88.2%** (15/17 seizures) | McNemar $p \approx 0.50$ (not significant at $N=17$) |
| **False-Alarm Rate** | **0.373 FA/h** (17 FAs / 45.63 h) | **0.307 FA/h** (14 FAs / 45.63 h) | Poisson 95% CIs overlap ([0.217, 0.597] vs [0.168, 0.515]) |
| **Median Latency** | **3.0 s** (Mean: 4.18 ± 2.5 s) | **11.0 s** (Mean: 10.8 s) | Proposed detects 8.0 s earlier |
| **Word-Length SQNR** | **82.6 dB** at $B=16$ bits | N/A (Floating Point) | Feature relative error $< 0.003\%$ |
| **Classification Cost** | **176 MACs** / second | Multi-kernel RBF-SVM | $> 100\times$ lower hardware complexity |

---

## 5. Hardware Specifications: RealDigital Boolean Board (Spartan-7 XC7S50)
- **FPGA Part Number:** `xc7s50csga324-1` (or `xc7s50csga342-1`)
- **System Clock:** 100 MHz oscillator connected to Pin `F14` (`LVCMOS33`).
- **USB-UART Interface:** Silicon Labs CP2102N bridge connected to FPGA Pin `V15` (RX) and `W15` (TX).
- **On-Chip Resources Available:**
  * 32,600 Slice LUTs
  * 65,200 Slice Registers (Flip-Flops)
  * 120 DSP48E1 slices
  * 75 Block RAMs (36 Kb each, or 150 of 18 Kb)
- **Project Resource Targets (Post-Implementation):**
  * Slice LUTs: $< 2{,}000$ ($< 6.1\%$)
  * Registers: $< 2{,}500$ ($< 3.8\%$)
  * DSP48E1 slices: $\le 2$ ($1.67\%$)
  * 18 Kb BRAM primitives: $\le 4$ ($2.67\%$)
  * Total On-Chip Power: $< 150\text{ mW}$ (dominated by quiescent clock power)
