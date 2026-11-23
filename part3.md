### PROJECT 2 — Real-Time Adaptive Noise Cancellation for Speech Using the LMS Algorithm

**B. Concept.** A classic and extremely well-documented FPGA project: take a noisy speech/audio signal plus a reference noise signal, and use an adaptive FIR filter (trained live, sample-by-sample, using the Least-Mean-Squares algorithm) to cancel the noise and recover the clean signal — the same principle behind noise-cancelling headphones and hands-free telephony.

**C. Signal processing problem.**
- *Input:* a "primary" signal (speech + noise) and a "reference" signal (correlated with the noise, e.g. a second microphone picking up mostly noise).
- *Problem:* the noise is not known in advance and may change over time, so a fixed filter cannot remove it — the filter coefficients must adapt.
- *Algorithm:* adaptive FIR filter with LMS coefficient update: `w[n+1] = w[n] + μ·e[n]·x[n]`.
- *Output:* the error signal `e[n]` (= primary − filter output) is the noise-cancelled speech.
- *Concepts:* FIR filtering/convolution, gradient-descent-based adaptive filtering, convergence and stability (step-size μ), correlation between reference and noise.

**D. Why it fits EE2000.** This is the single most standard "adaptive filtering" project in signal processing curricula worldwide — it directly demonstrates convolution, adaptive/statistical signal processing, and gives an intuitive, audible, demonstrable result (you can literally play "before" and "after" audio at your viva).

**E. Boolean Board implementation.**
```
Two audio inputs (primary + reference) → external Pmod ADC module(s)
  → [FPGA] N-tap adaptive FIR filter (DSP48 MACs)
  → [FPGA] LMS coefficient update logic (runs every sample)
  → [FPGA] error signal e[n] = primary - filter output
  → PWM audio output (3.5mm jack) for live listening
  → (optional) UART stream to PC for waveform/SNR plotting
```
The adaptive filter and the entire LMS update loop must run on the FPGA for this to be a genuine hardware project — this is the "hard, must-be-hardware" part; doing LMS adaptation in software and only playing back a precomputed result would not qualify.

**F. Hardware requirements.**
- *Required:* Boolean Board; at least one Pmod audio-input module (e.g., PmodMIC3-class MEMS mic — note: PmodMIC3 itself is now discontinued per Digilent, so check current stock or use a general 2-channel Pmod ADC such as PmodAD1 with an external electret mic + amplifier circuit) for capturing "primary" and "reference" signals; the on-board PWM audio-out jack (already present) for playback.
- *Optional:* a second identical mic module for a genuine 2-microphone reference setup, or a signal generator (even a phone) as a controllable "noise source" for repeatable testing.

**G. Algorithm.**
```
x[n] (reference) → Adaptive FIR filter (DSP48 MACs) [moderate]
                  → y[n] = w·x [easy, once filter exists]
d[n] (primary)  → e[n] = d[n] - y[n] [easy]
e[n], x[n]      → LMS update: w[n+1] = w[n] + μ e[n] x[n] [hard: must happen every sample, in fixed-point, without instability]
```
The LMS update loop is the hard part — it requires a multiply-accumulate per tap per sample, done in a pipelined, correctly-timed way, with careful step-size (μ) selection to avoid divergence — this is exactly the "coefficient drift/overflow" problem the literature below explicitly documents and solves.

**H. FPGA implementation challenges.**
- *Fixed-point:* weight overflow/drift is a **documented, real problem** in this exact application (see literature below) — plan for saturation logic or a leakage factor (Leaky LMS) from the start.
- *Throughput:* must complete filter + update within one audio sample period — trivial at typical speech sample rates (8–16 kHz) given the FPGA's clock speed, but still needs a clean pipelined design.
- *DSP usage:* N taps → roughly N DSP48 multiplies for filtering + N more for the update term, so an 8–16 tap filter is a very comfortable fit within 120 DSP48 slices.
- *Realistic solution:* Leaky LMS (adds a small leakage/forgetting term to the weight update) is explicitly reported in the literature to improve stability over plain LMS — a good, well-documented upgrade path for your "extension" work.

**I. Software simulation.** Prototype LMS in Python/MATLAB on recorded (or synthetically mixed) noisy speech, sweep step-size μ and filter length N, and generate: (1) SNR-before vs. SNR-after bar chart across conditions, (2) time-domain waveform of primary, reference, and recovered signal, (3) weight-convergence plot over time, (4) spectrogram before/after. Quantize the same algorithm to your target fixed-point format and re-verify in Python before porting to Verilog.

**J. Experimental metrics.** SNR improvement (dB) — the standard metric in every paper below; MSE of the error signal over time (to show convergence); convergence time (samples to reach steady-state); FPGA resource utilization; (optional) informal MOS-style subjective listening comparison for your viva demo.

**K. Literature.**
1. Widrow & Hoff-derived LMS algorithm — foundational; cite via any standard adaptive-filtering textbook (e.g., Haykin, *Adaptive Filter Theory*) rather than a single paper, since LMS itself long predates FPGA implementations.
2. "FPGA Implementation of Adaptive LMS Filter for Noise Cancellation Applications" — (cite index="56-1">the cancellation system is designed in Verilog HDL and tested for noise cancellation in a corrupted speech signal, synthesized with Quartus II and implemented on an Altera DE2 FPGA board</cite>. Directly reproducible target: same problem, same general toolflow (adapt Quartus/DE2 specifics to Vivado/Boolean Board).
3. "Implementation of Adaptive Filters Using LMS Algorithm on FPGA" (Academia.edu, citing Chu's *FPGA Prototyping by Verilog Examples*) — (cite index="53-1">describes an 8-bit, 5-tap adaptive filter implemented in hardware with combinational and sequential logic stages, including MATLAB validation at 10 dB SNR with Gaussian noise, and explicitly discusses synchronization/timing issues between the clock tick and stable output values</cite> — very close in scope to a first-semester student project; good template for your own tap-count/bit-width choices.
4. "Implementation of Efficient Adaptive Noise Cancellation on FPGA Using LMS and LLMS Algorithms" (IJRASET) — (cite index="58-1">compares standard LMS against Leaky LMS (LLMS) for real-time audio noise cancellation, reporting that LLMS achieves better SNR, PSNR, MSE and stability than standard LMS, after first validating both in MATLAB and then in Verilog/Xilinx ISE</cite>. Directly useful for your extension (LMS → LLMS comparison) with a clear reproducible metric set.
5. "Design and Implementation of FPGA-Based Adaptive Filter for Echo Cancellation" — (cite index="54-1">an adaptive filter implemented using Xilinx Vivado software/hardware co-design, where the LMS-based system's adaptive parameters are first derived from a MATLAB/Simulink model</cite> — useful for the MATLAB-to-Vivado co-design workflow specifically.

**L. Replication possibility.** Mid-term: reproduce an LMS-based SNR-improvement result in Python/MATLAB on a noisy-speech test case, matching the qualitative behavior reported in source 2 or 3 above (SNR improves, error converges). Final: your own contribution is the working fixed-point FPGA implementation with measured (not simulated) SNR improvement on hardware, plus — if time allows — the LMS-vs-LLMS stability comparison from source 4, reproduced yourselves.

**M. Extensions.**
1. Upgrade plain LMS to Leaky LMS or Normalized LMS (NLMS) and compare convergence/stability.
2. Test cancellation performance across multiple real noise types (fan noise, traffic, babble) and report SNR improvement per type.
3. Add a live "before/after" audio A/B demo mode for the viva (switch between raw and cancelled audio at the press of a button).
4. Explore variable-step-size LMS (μ adapts based on error magnitude) as a more advanced extension.

**N. Team-of-4 distribution.**
- *Member 1:* Literature review, LMS mathematical derivation, step-size/stability analysis.
- *Member 2:* Python/MATLAB simulation, SNR/MSE measurement pipeline, all report plots.
- *Member 3:* Verilog RTL for the FIR filter + LMS update datapath, testbenches.
- *Member 4:* Fixed-point verification, Pmod audio front-end wiring/integration, live demo setup and hardware testing.

**O. Expected difficulty: Moderate.** Extremely well-trodden literature (many closely-matching papers to replicate), but getting the *fixed-point* adaptive update loop stable in real hardware (not just in floating-point Python) is a genuine, well-documented engineering challenge.

**P. Time feasibility.**
- Literature review: 1 week
- Python/MATLAB simulation + tuning: 2 weeks
- Fixed-point conversion + stability testing: 1.5 weeks
- Verilog implementation: 2–3 weeks
- Hardware integration + testing: 1.5 weeks
- Report/presentation: ongoing + 1 week
- **Flag:** weight overflow/instability in fixed-point is the most likely failure point — budget explicit time for saturation-logic debugging, and prototype the Leaky-LMS variant early rather than as an afterthought if plain LMS proves unstable on hardware.
