# Technical Audit: End-to-End Dataflow & Timing Analysis
**Project:** FPGA-Based Real-Time Multichannel EEG Seizure Detection  
**Target Hardware:** RealDigital Boolean Board (AMD Spartan-7 `xc7s50csga324-1`)  
**Clock Domain:** 100.000 MHz Single Synchronous Clock ($T_{\text{clk}} = 10.0$ ns)  
**Audit Date:** November 2026  

---

## 1. End-to-End Dataflow Progression

The hardware datapath processes incoming scalp EEG data through six sequential pipeline stages, transforming raw serial bytes into clinical seizure alarms in real time:

```text
Host PC (Python Streamer)
   │  [230,400 baud, 8N1]
   ▼
[Stage 0: UART Receiver & Packet Decoder]
   │  Bytes: 0xAA -> ch_id -> MSB -> LSB
   │  Throughput: 22,528 bytes/sec (97.77% link duty cycle)
   ▼
[Stage 1: 22-Channel Time-Multiplexed IIR Biquad]
   │  Causal 0.5 - 25 Hz 4th-order Butterworth (2 DF1 sections)
   │  Latency: 6 clock cycles (60 ns) per sample
   ▼
[Stage 2: 5-Level Dyadic Daubechies-4 DWT Cascade]
   │  Modular serial MAC (8 cycles/level) + 8-entry serialization FIFO
   │  Decimated Subbands: D3 (32/s), D4 (16/s), D5 (8/s), A5 (8/s)
   ▼
[Stage 3: Ping-Pong Feature Accumulator]
   │  1.0 s non-overlapping window (256 frames = 5,632 samples)
   │  Energy (38-bit acc) & Line-Length (26-bit acc) across 88 bins
   │  Drain Delay: 128 cycles (1.28 µs) -> hop_sync strobe
   ▼
[Stage 4: Linear SVM Classifier Engine]
   │  176-cycle serial MAC with 40-bit accumulator
   │  Evaluates: Score = b_eff + sum(w_eff * feat)
   │  Execution Time: 1.76 µs
   ▼
[Stage 5: Alarm Logic, Display & Telemetry]
   │  Persistence filter: k in {1, 2, 3, 5} consecutive positive windows
   │  Refractory blanking: 30 seconds
   ▼
Board Indicators (LED15 Strobe, RGB0 Flashing Red, 7-Seg) & UART TX Telemetry (0xA5)
```

---

## 2. Timing Budget & Hardware Utilization Analysis

The design operates on a single 100.0 MHz system clock ($T_{\text{clk}} = 10.0$ ns). The complete timing budget for one sampling interval ($T_s = 1 / 256\text{ Hz} \approx 3.90625$ ms) is detailed below:

### 2.1 UART Ingestion Timing
* **Baud Rate:** 230,400 baud $\implies 1\text{ bit} = 434\text{ clock cycles} = 4.34\,\mu\text{s}$.
* **Byte Duration (10 bits: 1 start, 8 data, 1 stop):**
  $$T_{\text{byte}} = 10 \times 434\text{ cycles} = 4{,}340\text{ clock cycles} = 43.4\,\mu\text{s}$$
* **Sample Frame Duration (4 bytes: `0xAA`, `ch_id`, `MSB`, `LSB`):**
  $$T_{\text{sample}} = 4 \times 4{,}340\text{ cycles} = 17{,}360\text{ clock cycles} = 173.6\,\mu\text{s}$$
* **Complete 22-Channel Time Step (22 samples = 88 bytes):**
  $$T_{\text{step}} = 22 \times 17{,}360\text{ cycles} = 381{,}920\text{ clock cycles} = 3.8192\text{ ms}$$
* **Theoretical Time Step Period at 256 Hz:**
  $$T_s = \frac{100{,}000{,}000\text{ cycles/s}}{256\text{ Hz}} = 390{,}625\text{ clock cycles} = 3.90625\text{ ms}$$
* **UART Link Duty Cycle:**
  $$\text{Duty Cycle} = \frac{381{,}920}{390{,}625} \times 100\% = \mathbf{97.77\%}$$
  *Confirmed Fact:* The serial link operates with only $2.23\%$ idle slack ($8{,}705$ clock cycles $\approx 87.05\,\mu\text{s}$ per time step). Any host transmission stutter exceeding $87\,\mu\text{s}$ will cause packet backlog or inter-frame jitter.

### 2.2 Processing Latency vs. Throughput Slack
Between the arrival of successive channel samples, there are $17{,}360$ clock cycles ($173.6\,\mu\text{s}$) of idle time. The hardware datapath completes its computations in a tiny fraction of this interval:

| Pipeline Stage | Active Computation Time | Idle Cycles per Sample | Hardware Active Duty Cycle |
|---|---|---|---|
| **IIR Biquad Filter** | 5 clock cycles ($50$ ns) | $17{,}355$ cycles ($173.55\,\mu\text{s}$) | $0.029\%$ |
| **DWT Level 1** | 8 clock cycles ($80$ ns, on decimation phase 1) | $34{,}712$ cycles (every 2 samples) | $0.023\%$ |
| **DWT Level 2** | 8 clock cycles ($80$ ns, every 4 samples) | $69{,}432$ cycles | $0.012\%$ |
| **DWT Level 3** | 8 clock cycles ($80$ ns, every 8 samples) | $138{,}872$ cycles | $0.006\%$ |
| **DWT Level 4** | 8 clock cycles ($80$ ns, every 16 samples) | $277{,}752$ cycles | $0.003\%$ |
| **DWT Level 5** | 8 clock cycles ($80$ ns, every 32 samples) | $555{,}512$ cycles | $0.001\%$ |
| **Feature Accumulator Write** | 1 clock cycle ($10$ ns per coefficient) | Synchronous with DWT pop | $<0.01\%$ |

*Conclusion:* The single time-multiplexed datapath is idle $> 99.9\%$ of the time, proving that sharing hardware across 22 channels easily meets real-time constraints with zero throughput bottlenecks.

### 2.3 Window Boundary Flush & Classification Latency
When the final sample of a 1.0-second window arrives (Sample 255 of Channel 21):
1. **Pipeline Flush Timer (`hop_drain_cnt`):**
   - Counts 128 clock cycles ($1.28\,\mu\text{s}$).
   - This drains all 5 cascaded DWT serial levels ($5 \times 8 = 40$ cycles) and the 8-entry output queue ($8$ cycles).
2. **Ping-Pong Buffer Swap:**
   - At cycle 128, `hop_sync` asserts for 1 clock cycle ($10$ ns).
   - `active_buf` swaps to the alternate bank; `stream_buf` begins serialization.
3. **SVM Classification Burst:**
   - Serializes all 176 features to the SVM classifier in exactly 176 consecutive clock cycles ($1.76\,\mu\text{s}$).
4. **Alarm Post-Processing:**
   - Evaluated on cycle 177 upon `svm_done` assertion ($10$ ns).
5. **Total End-to-End Latency from Last Sample to Alarm Assertion:**
   $$T_{\text{latency}} = 128\text{ (flush)} + 176\text{ (SVM)} + 1\text{ (alarm)} = \mathbf{305\text{ clock cycles} = 3.05\,\mu\mathbf{s}}$$
   The entire feature extraction and classification process completes in $3.05\,\mu\text{s}$, well within the 1-second clinical window hop.

---

## 3. Mathematical Transformations & Word-Length Scaling

The table below tracks the complete evolution of arithmetic data representations across the entire FPGA datapath:

| Subsystem | Signal Name | Data Type & Width | Fixed-Point Format | Numerical Range | Scaling Factor |
|---|---|---|---|---|---|
| **Input Stream** | `sample_in` | Signed 16-bit | $Q1.15$ | $[-32768, 32767]$ | $S_{\text{sig}} = 20\text{ LSB}/\mu\text{V}$ ($\pm 1638.4\,\mu\text{V}$) |
| **IIR Coefficients** | `S0_B*`, `S0_A*`, `S1_B*`, `S1_A*` | Signed 25-bit | $Q5.20$ | $[-16\times 10^6, 16\times 10^6]$ | $2^{20} = 1{,}048{,}576$ |
| **IIR State RAM** | `s0_mem_y*`, `s1_mem_y*` | Signed 34-bit | $Q14.20$ | $[-8.59\times 10^9, 8.59\times 10^9]$ | $2^{20}$ internal guard scaling |
| **IIR Products** | `fb0_prod_reg`, `fb1_prod_reg` | Signed 60-bit | $Q19.40$ | $\approx \pm 5.76\times 10^{17}$ | $2^{40}$ product scaling |
| **IIR Output** | `sample_out` | Signed 16-bit | $Q1.15$ | $[-32768, 32767]$ | Saturated 16-bit signed integer |
| **DWT Taps** | `get_h()`, `get_g()` | Signed 16-bit | $Q1.15$ | $[-32768, 32767]$ | $2^{15} = 32{,}768$ |
| **DWT Products** | `prod_h`, `prod_g` | Signed 32-bit | $Q2.30$ | $[-2^{31}, 2^{31}-1]$ | $2^{30}$ |
| **DWT Accumulator**| `acc_h`, `acc_g` | Signed 36-bit | $Q6.30$ | $[-2^{35}, 2^{35}-1]$ | 4 guard bits for 8-tap sum |
| **DWT Output** | `coeff_out` | Signed 16-bit | $Q1.15$ | $[-32768, 32767]$ | `(acc + 16384) >>> 15`, saturated |
| **Energy Product** | `sq_coeff` | Unsigned 32-bit | $Q2.30$ | $[0, 2^{32}-1]$ | $c^2 \ge 0$ |
| **Energy Accum** | `energy_b0`, `energy_b1` | Unsigned 38-bit | $Q8.30$ | $[0, 2^{38}-1]$ | 6 guard bits ($\sum_{i=1}^{32} c^2$) |
| **Line-Length Diff**| `abs_diff` | Unsigned 16-bit | $Q1.15$ | $[0, 32767]$ | 17-bit safe subtraction |
| **Line-Length Accum**| `ll_b0`, `ll_b1` | Unsigned 26-bit | $Q11.15$ | $[0, 2^{26}-1]$ | 10 guard bits ($\sum_{i=1}^{31} \|\Delta c\|$) |
| **Feature Data** | `feat_data` | Signed 19-bit | $Q4.15$ | $[0, 32767]$ | Normalized, rounded, saturated |
| **SVM Weights** | `weight_data` | Signed 16-bit | $Q1.15$ | $[-32768, 32767]$ | $S_M = 1500$ scaling factor |
| **SVM Bias** | `bias_data` | Signed 32-bit | $Q2.30$ | $\mathtt{0xFFF43986}$ ($-771706$) | Folded $b_{\text{eff}} \times S_M$ |
| **SVM Product** | `prod` | Signed 32-bit | $Q2.30$ | $[-2^{31}, 2^{31}-1]$ | $16\text{-bit} \times 16\text{-bit}$ DSP48 product |
| **SVM Accumulator**| `accum` | Signed 40-bit | $Q10.30$ | $[-2^{39}, 2^{39}-1]$ | 8 guard bits against 176-sum overflow |

---

## 4. Buffering Mechanisms & Contention Avoidance

### 4.1 DWT Output Serialization Queue
* **Problem:** In a dyadic DWT tree, downsampling by 2 at each level causes decimation phases to align intermittently. On specific input samples, Level 3 ($D_3$), Level 4 ($D_4$), and Level 5 ($D_5, A_5$) can finish their 8-tap serial MAC calculations on the same clock cycle, producing up to 4 coefficients simultaneously.
* **Resolution in RTL (`dwt_db4.v`):**
  - An 8-entry circular FIFO (`queue_mem[0:7]`) decouples the multi-level filter engines from the downstream feature accumulator.
  - While `pop_valid == 1` (`q_count > 0`), one coefficient is popped every cycle and presented to the feature accumulator.
  - The enqueue logic prioritizes Level 5 (enqueues 2 entries: $D_5$ and $A_5$), Level 4 (enqueues $D_4$), and Level 3 (enqueues $D_3$). Because samples arrive at least $17{,}360$ clock cycles apart over UART, the queue completely empties within 8 cycles, guaranteeing zero queue overflow during live streaming.

### 4.2 Feature Accumulator Ping-Pong Double Buffering
* **Problem:** In a continuous real-time monitor, feature accumulation over a 1.0-second window must transition atomically to the next window. If accumulation and serialization share a single memory bank, the first coefficients of window $W+1$ arrive while window $W$ is still being streamed to the SVM classifier, causing data overwrites or stalls.
* **Resolution in RTL (`feature_accumulator.v`):**
  - Two independent banks (Bank 0 and Bank 1) of 88 bins each.
  - When `window_sync` fires, `active_buf` toggles (`active_buf <= ~active_buf`).
  - New DWT coefficients for window $W+1$ accumulate into the new active bank without interference.
  - The previous bank becomes `stream_buf`, which is read out sequentially over 176 cycles to feed the SVM classifier.
  - As each bin is read out, the read address clears the bin to zero on-the-fly (`wdata_b*_e <= 0`, `wdata_b*_ll <= 0`), preparing it for the next window swap with zero dedicated reset cycles.
