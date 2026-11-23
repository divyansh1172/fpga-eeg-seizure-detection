# EE2000 Final Project: Viva Defense Battlecard & Technical Q&A
**Course:** EE2000 Signal Processing, Fall 2026, IIT Hyderabad  
**Team 15:** Real-Time Multichannel EEG Seizure Detection on FPGA (DWT + Linear SVM)  
**Target:** RealDigital Boolean Board (AMD Spartan-7 XC7S50)  
**Weight:** 5% of Total Grade (Presentation + Board Demonstration + Oral Viva)

---

## 1. Top 10 Anticipated Viva Questions & Examiner Defense

### Q1: Why did you choose DWT + Linear SVM instead of a modern Deep Learning model (e.g., 1D-CNN or Transformer)?
- **Defense Answer:**
  1. *Deterministic Timing & Low Power:* On an embedded FPGA targeting closed-loop therapeutic stimulation or wearable seizure detection, deep CNNs and Transformers require millions of MAC operations and megabytes of weight parameters, necessitating external DDR memory and dissipating hundreds of milliwatts.
  2. *Single DSP48 Slice:* Our 5-level db4 DWT and Linear SVM requires strictly **176 MAC operations per 1-second epoch**, fitting entirely within 2 DSP48E1 slices and dissipating $< 150\text{ mW}$ on the Spartan-7.
  3. *Small-Sample Cohort Reality:* In patient-specific seizure detection, each patient typically has only 3 to 7 recorded seizures. High-capacity neural networks severely overfit on such small sample sizes, whereas a strongly regularized Linear SVM with balanced class weights generalizes cleanly without overfitting.

---

### Q2: A Xilinx DSP48E1 multiplier port is $25 \times 18$ bits. Table 7 shows your raw Energy accumulator is 38 bits wide. How can you feed it into the DSP48E1 slice in a single clock cycle without cascading slices?
- **Defense Answer:**
  - *The Math:* In Q1.15 fixed-point arithmetic, squaring a 16-bit coefficient generates a Q2.30 product scaled by $2^{30}$. Accumulating $N_b \le 64$ samples produces a 38-bit sum ($\lceil \log_2 64 \rceil + 32 = 38\text{ bits}$).
  - *The Solution (Zero LUT Cost):* At the accumulator output, we perform an offline-aligned **hardware wire-shift**: we drop the 15 fractional LSBs from the squaring and right-shift by $\log_2(N_b) \in \{6, 5, 4, 4\}$:
    $$X_{\text{E,norm}} = X_{\text{E,raw}}[34 : 15 + \log_2(N_b)]$$
  - This normalizes the Energy sum down to $\le 19\text{ bits}$ on the exact same numerical scale as the 23-bit Line-Length accumulator. Both fit natively into the 25-bit signed multiplier port of a single DSP48E1 slice in 1 clock cycle with zero LUT overhead and zero weight underflow in Q1.15 BRAM.

---

### Q3: In Section 5.2, you mention an impulse-response memory span of 218 samples ($0.85\text{ s}$) but claim a group delay of only $\approx 0.25\text{ s}$. Why the difference?
- **Defense Answer:**
  - *Span vs. Group Delay:* The 5-level dyadic cascade of $L=8$-tap db4 filters has a causal memory length of $(L-1)(2^J - 1) = 7 \times 31 = 217\text{ samples}$ ($218\text{ taps} \implies 0.85\text{ s}$ at $256\text{ Hz}$). This is the *maximum memory duration* before the impulse response completely decays to zero.
  - *Extremal-Phase Property:* Standard Daubechies-4 is a minimum-phase / extremal-phase wavelet, not a symmetric linear-phase FIR filter. Its filter energy is heavily concentrated in the first few taps.
  - *Passband Delay:* The effective group delay (the center-of-mass of the impulse response in the passband) is approximately $0.20\text{--}0.25\text{ s}$. Both the Python streaming pipeline and the Verilog RTL share this causal delay identically.

---

### Q4: Channels 3 (`T7-P7`) and 19 (`P7-T7`) in CHB-MIT have inverted electrode polarities ($y = -x$). How does your pipeline handle this?
- **Defense Answer:**
  - *Sign Invariance of Features:* The two extracted wavelet features are Sub-band Energy ($E = \frac{1}{N_b} \sum c[n]^2$) and Line-Length ($LL = \frac{1}{N_b-1} \sum |c[n] - c[n-1]|$).
  - Squaring is an even function: $(-c[n])^2 = c[n]^2$.
  - Absolute difference is sign-invariant: $|(-c[n]) - (-c[n-1])| = |-(c[n] - c[n-1])| = |c[n] - c[n-1]|$.
  - Therefore, both channels yield mathematically identical feature trajectories regardless of montage polarity inversion.

---

### Q5: How does offline weight folding save FPGA resources and latency?
- **Defense Answer:**
  - The standard SVM decision equation is $f(\mathbf{x}) = \sum_i w_i \left( \frac{\frac{1}{S_i} X_i - \mu_i}{\sigma_i} \right) + b$. Implementing this in hardware requires 176 dividers (or multi-cycle fixed-point reciprocal multipliers) and subtractors.
  - By rearranging the linear equation offline:
    $$w_{\text{eff},i} = \frac{w_i}{\sigma_i S_i}, \quad b_{\text{eff}} = b - \sum_i \frac{w_i \mu_i}{\sigma_i}$$
  - The FPGA evaluates $f(\mathbf{X}) = \sum_i w_{\text{eff},i} X_i + b_{\text{eff}}$ directly on raw accumulator sums $X_i$ using a single DSP48E1 slice in strictly 176 clock cycles ($1.76\ \mu\text{s}$ at 100 MHz) with zero hardware dividers.

---

### Q6: In your ablation study, why does $k=1$ persistence yield *lower* sensitivity ($88.2\%$) than $k=3$ ($100.0\%$)? Shouldn't an easier alarm threshold detect more seizures?
- **Defense Answer:**
  - *Premature Refractory Masking:* At $k=1$, single-window transient artifacts trigger frequent false alarms ($3.12\text{ FA/h}$).
  - When a false alarm triggers within 30 seconds immediately prior to clinical onset, the mandatory 30-second refractory blanking suppresses all alarms during the true seizure onset, causing the scoring protocol to register a missed seizure.
  - Requiring $k=3$ consecutive positive windows effectively filters out isolated spikes, preventing premature refractory suppression and restoring $100.0\%$ event sensitivity.

---

### Q7: Your baseline achieves $100.0\%$ sensitivity, whereas your Shoeb replication achieves $88.2\%$. Is this difference statistically significant?
- **Defense Answer:**
  - *Honest Statistical Maturity:* On our 3-subject cohort ($N=17$ seizures), the two discordant seizures are `chb01_04` (28 s) and `chb01_18` (65 s).
  - McNemar's test for paired binary outcomes yields $p \approx 0.50$, indicating the difference is **not statistically significant** at $N=17$.
  - Furthermore, Poisson 95% confidence intervals for false-alarm rates overlap ([0.217, 0.597] FA/h for baseline vs [0.168, 0.515] FA/h for Shoeb). We report this transparently: our primary advantage over Shoeb is not superior statistical sensitivity, but rather an $8.0\text{ s}$ faster median latency and over $100\times$ lower computational complexity suitable for edge FPGA deployment.

---

### Q8: In the word-length study, why do you choose $B=16$ bits if $B=14$ bits also meets the operational targets?
- **Defense Answer:**
  - *Native FPGA Block RAM Alignment:* The Spartan-7 Block RAM primitives are configured as 18 Kb blocks (typically 16-bit data + 2-bit parity, or 16-bit half-words). Storing 16-bit samples and weights maps natively to byte and half-word addresses without packing or unpacking logic.
  - *Headroom:* $B=16$ bits provides $82.6\text{ dB}$ SQNR ($0.003\%$ relative feature distortion), guaranteeing sub-microvolt numerical noise well below the $0.5\ \mu\text{V}$ physiological EEG noise floor.

---

### Q9: How does the UART link at 230,400 baud simulate real-time playback?
- **Defense Answer:**
  - 22 channels at $256\text{ Hz}$ equals $5{,}632\text{ samples/s}$. Each sample is framed into a 4-byte packet (`0xAA`, channel ID, MSB, LSB), requiring $22{,}528\text{ bytes/s}$.
  - At 230,400 baud (10 bits per byte including start/stop), the link throughput is $23{,}040\text{ bytes/s}$ ($\approx 97.8\%$ link utilization).
  - The host Python script sleeps for $3.906\text{ ms}$ between consecutive 22-channel sample frames, reproducing real-time continuous electrode streaming with sub-millisecond pacing.

---

### Q10: How does your Spartan-7 implementation compare against custom ASICs (e.g., Altaf et al. 2015, Alghaihab et al. 2022)?
- **Defense Answer:**
  - Custom ASICs (e.g., 65nm / 180nm CMOS) achieve microwatt-level power dissipation ($< 1\text{ mW}$) by fabricating application-specific hardware accelerators and custom analog front-ends.
  - Our design targets an off-the-shelf, low-cost commercial FPGA (RealDigital Boolean Board, Spartan-7 XC7S50). While our total on-chip power ($\approx 100\text{--}150\text{ mW}$) is higher due to FPGA static configuration overhead and 100 MHz clock tree distribution, our active signal-processing datapath requires $< 2{,}000$ LUTs and $< 2$ DSP slices, proving that real-time multi-channel wavelet classification is feasible on low-cost reconfigurable hardware without custom silicon fabrication.
