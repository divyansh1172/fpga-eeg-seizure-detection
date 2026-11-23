## 4. Important Hardware Constraints (summary for quick reference)

1. **No audio/ECG/image input path exists without buying a Pmod module.** Budget for this now — see Section 6 for a shortlist-specific cost breakdown.
2. **337 KB of BRAM is the hard ceiling** for anything that needs to buffer a signal, image, or dataset on-chip. Plan buffer sizes in bytes early — this is the resource most projects run out of first, not logic cells.
3. **120 DSP48 slices** comfortably cover a moderate FIR filter (tens of taps), an FFT (with a streaming/pipelined core), or a handful of MAC-heavy blocks in parallel — but not several large algorithms simultaneously.
4. **The on-board ADC is 1 channel, tied to a physical potentiometer** — it is not a general-purpose signal-acquisition input. Don't assume you can just "use the on-board ADC" for an external analog signal; you need to route to the Pmod XADC auxiliary pins instead, respecting the ≤1V peak-to-peak and biasing requirements in Xilinx UG480.
5. **Audio out is PWM/PDM through a fixed 50 Hz–5 kHz bandpass filter** — fine for demonstrating filtered speech-band audio, not for high-fidelity or ultrasonic work.
6. **HDMI is output only.** Any "camera → FPGA" idea needs a separate camera module; you cannot pull video in through the HDMI port.
7. **Vivado targets part `xc7s50csga342-1`** — make sure your team downloads the correct Boolean Board board files (Xilinx's official board store does not include this board by default; use the community board-file repository referenced in Section 12, or whatever your course provides).

---

## 5. Project Ideas

Eight ideas are presented, deliberately spanning easy, medium, and ambitious. They are **not ranked**. Each follows the full template you specified.

---

### PROJECT 1 — Real-Time QRS Complex Detection for Heart-Rate Estimation from ECG

**B. Concept.** Your team builds a system that takes a real (or recorded, replayed) ECG signal, filters out noise, and automatically detects the "QRS complex" — the sharp spike in every heartbeat — in real time on the FPGA, then computes and displays heart rate. This is the classic Pan–Tompkins algorithm, originally published in 1985 and still the reference method taught in every biomedical signal processing course.

**C. Signal processing problem.**
- *Input:* an ECG waveform, either from a real biopotential front-end or replayed from a standard database (MIT-BIH Arrhythmia Database) stored in BRAM.
- *Noise/problem:* baseline wander, powerline interference (50/60 Hz), muscle noise (EMG artifact), motion artifacts.
- *Algorithm:* bandpass filter (5–15 Hz) → derivative → squaring → moving-window integration → adaptive thresholding → QRS detection → RR-interval → heart rate.
- *Output:* detected R-peak locations, instantaneous heart rate (BPM), displayed on 7-segment display; optionally the filtered waveform via UART to a PC for plotting.
- *Concepts:* digital FIR/IIR filtering, differentiation as a discrete-time operation, nonlinear (squaring) operations, moving-average integration, adaptive thresholding/detection theory.

**D. Why it fits EE2000.** Directly exercises filtering, convolution (the FIR bandpass and derivative are convolutions), detection theory (thresholding is a classical detection problem), and time-domain feature extraction — all core signal processing topics, with a genuinely clinical, well-documented target algorithm.

**E. Boolean Board implementation.**
```
ECG electrodes → analog front-end (external Pmod/module)
  → Pmod XADC auxiliary input (or dedicated ADC Pmod)
  → [FPGA] bandpass FIR filter
  → [FPGA] derivative filter
  → [FPGA] squaring (DSP48 multiplier)
  → [FPGA] moving-window integrator
  → [FPGA] adaptive threshold + peak detect
  → [FPGA] RR-interval → BPM calculation
  → 7-segment display (BPM) + LED heartbeat blink + UART waveform stream (PC-side plot)
```
Everything from the bandpass filter onward **must run on the FPGA fabric** in Verilog for this to count as a real Boolean Board project — using Python/MATLAB only to *pre-verify* the algorithm before porting it is fine and expected, but a design that does the detection in software and only *displays* results on the board would not qualify.

**F. Hardware requirements.**
- *Required:* Boolean Board; an ECG analog front-end module (e.g., an AD8232-based single-lead ECG breakout board) wired into a Pmod header via the XADC auxiliary pins, or replayed test data stored in BRAM for the mid-term stage.
- *Optional:* real ECG electrodes + safety-isolated front-end for a live human-subject demo (see Section 9 — Failure Modes for a strong recommendation to primarily demo with recorded/replayed MIT-BIH data rather than live-subject ECG, for both safety and reliability reasons).

**G. Algorithm.**
```
ECG in → Bandpass FIR (5-15 Hz) [moderate]
       → Derivative filter (5-point) [easy]
       → Squaring (single DSP48 multiply) [easy]
       → Moving-window integrator (~150 ms window) [moderate]
       → Adaptive threshold + refractory-period logic [hard]
       → RR interval counter → BPM [easy]
```
The adaptive thresholding/refractory logic is the hardest block — it's a small state machine with several tunable parameters (thresholds evolve based on recent peak/noise levels), and getting this exactly right against a fixed sample rate in hardware (vs. easy vectorized code in Python) is the main engineering challenge.

**H. FPGA implementation challenges.**
- *Fixed-point:* ECG amplitudes are small (mV range); you'll want Q-format fixed-point (e.g., Q1.15) with care to avoid underflow in the derivative/squaring stages.
- *Latency/throughput:* trivial — ECG sample rates (250–360 Hz typical) are far below what the FPGA can process; the challenge is correctness, not speed.
- *Memory:* storing a full test record (e.g., 30 s at 360 Hz, 12-bit samples) is manageable in BRAM (~16 KB).
- *DSP usage:* light — a handful of DSP48 slices suffice.
- *Realistic solution:* develop and validate the fixed-point behavior bit-exactly in Python first (quantize your Python model to match your Verilog's fixed-point format) before writing RTL — this catches most fixed-point bugs before synthesis.

**I. Software simulation.** Implement Pan–Tompkins in Python against the MIT-BIH Arrhythmia Database (freely available via PhysioNet), verify QRS detection accuracy against the database's official annotations, and generate: (1) raw vs. filtered ECG plot, (2) each intermediate stage's waveform, (3) detected R-peaks overlaid on the signal, (4) a sensitivity/positive-predictivity table compared to ground truth. Then re-implement the same fixed-point-quantized algorithm in Verilog and compare outputs sample-by-sample against your Python reference in a testbench before touching hardware.

**J. Experimental metrics.** QRS detection sensitivity (Se) and positive predictivity (+P) against MIT-BIH annotations (standard metrics used by every paper in this space, per ANSI/AAMI EC38); heart-rate estimation error (BPM); FPGA resource utilization (LUTs, DSP48s, BRAM); latency from R-peak occurrence to detection.

**K. Literature.**
1. J. Pan and W. J. Tompkins, "A Real-Time QRS Detection Algorithm," *IEEE Transactions on Biomedical Engineering*, 1985. — the foundational algorithm; you will directly reproduce this. Widely cited, available via IEEE Xplore.
2. Pavlatos, Dimopoulos, Papakonstantinou, "Hardware Implementation of Pan & Tompkins QRS Detection Algorithm" — <cite index="46-1">a hardware implementation of the Pan and Tompkins QRS detection algorithm described in Verilog HDL, simulated, synthesized and tested on a Xilinx FPGA board using the European ST-T database, reporting a 250% speedup over software</cite>. Directly reproducible target architecture and result. (Semantic Scholar / ResearchGate — verify DOI on IEEE Xplore before citing formally.)
3. FPGA Implementation of ECG Feature Extraction Using Time-Domain Analysis (arXiv, 1802.03310) — <cite index="47-1">describes a Pan-Tompkins-based QRS detector and feature extractor implemented on a Virtex-6 FPGA, with resource utilization and timing tables showing small combinational delay enabling real-time operation</cite>. Freely available on arXiv — good for architecture-level reference.
4. "An Efficient Architecture for QRS Detection in FPGA Using Integer Haar Wavelet Transform," *Circuits, Systems, and Signal Processing* (Springer) — an alternative (wavelet-based) FPGA QRS architecture, useful for your "extension" work if you want to compare against Pan-Tompkins.
5. "Assessing ECG-QRS Signal Detection Algorithm Chip and Simulation on Several FPGAs," *Discover Computing* (Springer, 2025) — <cite index="50-1">a power-efficient version of the Pan-Tompkins QRS extraction technique using a shifting-window mean to remove high-frequency noise and FFT to remove baseline drift, evaluated for accuracy, sensitivity and specificity</cite> — recent, gives you a modern point of comparison.

**L. Replication possibility.** Mid-term target: reproduce Pan-Tompkins QRS detection in Python against a MIT-BIH record and report Se/+P numbers matching the published range (>99% Se is typical on clean records). Final: your own contribution is the **fixed-point FPGA Verilog implementation** itself plus a resource/latency comparison against at least one of the papers above, and (optional extension) testing robustness against the MIT-BIH Noise Stress Test Database.

**M. Extensions.**
1. Add an arrhythmia flag (e.g., detect abnormally short/long RR intervals) as a simple rule-based classifier on top of your QRS detector.
2. Test and report robustness against the MIT-BIH Noise Stress Test Database at multiple SNR levels.
3. Compare Pan-Tompkins against a wavelet-based or second-derivative-based detector, both in Python and (if time allows) in hardware.
4. Add a live-subject demo mode using a safety-appropriate ECG front-end, with a clear safety/isolation writeup (strongly recommend consulting your instructor/TA before attempting any live-subject electrical connection).

**N. Team-of-4 distribution.**
- *Member 1:* Literature review, algorithm mathematical formulation, adaptive threshold design.
- *Member 2:* Python reference implementation + MIT-BIH validation + all report plots/metrics.
- *Member 3:* Verilog RTL (filter chain, integrator, threshold state machine) + testbenches.
- *Member 4:* Fixed-point conversion/verification, hardware integration (ADC front-end wiring, display driver), final-demo hardware testing.

**O. Expected difficulty: Moderate.** The algorithm itself is simple and well-documented; the difficulty is entirely in getting adaptive thresholding right in fixed-point hardware and in sourcing/wiring a real ECG front-end safely.

**P. Time feasibility.**
- Literature review: 1 week
- Algorithm dev (Python): 2 weeks
- Fixed-point conversion + verification: 1–1.5 weeks
- Verilog implementation: 2–3 weeks
- Hardware integration/testing: 1–2 weeks
- Report/presentation prep: ongoing + 1 dedicated week
- **Flag:** live-subject ECG acquisition is the piece most likely to overrun or fail outright (noise, safety, front-end procurement delay) — build the entire pipeline against replayed MIT-BIH data first, and treat live acquisition as a stretch goal, not the critical path.
