### PROJECT 3 — Real-Time Multi-Band Digital Audio Equalizer

**B. Concept.** A parallel bank of digital bandpass filters splits an incoming audio signal into frequency bands (e.g., bass/mid/treble or more bands), lets the user boost or cut each band independently using the board's switches, and recombines the result — exactly like the equalizer on a stereo system, but implemented entirely in FPGA hardware.

**C. Signal processing problem.**
- *Input:* live or replayed audio signal.
- *Processing:* a bank of parallel FIR (or IIR) bandpass filters split the spectrum; each band is scaled by a user-controlled gain; bands are summed back together.
- *Output:* the equalized audio signal, played back via PWM audio out; optionally, per-band energy shown on LEDs as a simple spectrum-style visualizer.
- *Concepts:* FIR/IIR filter design, frequency response and filter banks, gain/scaling, basic real-time DSP pipeline design, sampling-rate considerations.

**D. Why it fits EE2000.** This is the most direct, intuitive demonstration of "frequency-domain thinking implemented as a time-domain filter" — the frequency response, passband/stopband tradeoffs, and filter-order-vs-sharpness tradeoffs are all core Signal Processing 101 concepts, and the live, audible, switch-controlled demo is extremely effective in a viva.

**E. Boolean Board implementation.**
```
Audio in → external Pmod audio-in module
  → [FPGA] parallel filter bank (N bandpass FIR/IIR filters)
  → [FPGA] per-band gain multiply (controlled by on-board switches)
  → [FPGA] summation
  → PWM audio out (3.5mm jack)
  → LEDs: per-band energy display (optional visualizer)
```
The entire filter bank, gain control, and summation must run on the FPGA — this is squarely within what Verilog is naturally good at (fully parallel filter banks are exactly the kind of workload that benefits from FPGA parallelism vs. sequential software).

**F. Hardware requirements.**
- *Required:* Boolean Board; a Pmod audio-input module (mic or line-level ADC — same sourcing note as Project 2); on-board switches (already present, used for gain control); on-board PWM audio-out (already present).
- *Optional:* headphones/small speaker for a good demo; a signal generator or phone audio source for controlled test tones during development.

**G. Algorithm.**
```
Audio in → Filter bank: N parallel FIR bandpass filters [moderate — straightforward once one filter works, but N filters in parallel needs resource planning]
         → Per-band gain (switch-controlled multiply) [easy]
         → Sum all bands [easy]
         → Output
```
This is the **easiest** of the 8 ideas in this report — every individual block is a standard, well-taught DSP building block, and there's no adaptive or nonlinear logic anywhere in the pipeline.

**H. FPGA implementation challenges.**
- *Fixed-point:* modest — audio-band filtering with reasonable word widths (e.g., 16-bit) is very forgiving; no adaptive-loop stability issues like Project 2.
- *DSP usage:* N filters × filter order taps = total multiplies; with, say, 4 bands × 20-tap filters, this is comfortably within 120 DSP48 slices.
- *Latency/throughput:* trivial at audio sample rates.
- *Realistic solution:* this project has essentially no "hard" hardware challenge — the main engineering work is filter design (choosing band edges, filter order, and window/design method) and clean modular Verilog structure, not overcoming a resource or stability limit.

**I. Software simulation.** Design each bandpass filter in Python (`scipy.signal`) using windowed-sinc or Parks-McClellan (equiripple) design, plot each filter's frequency response, verify the filter bank sums back to (approximately) a flat response at unity gain, and simulate a few example EQ curves (e.g., "bass boost," "treble cut") on a test audio clip with before/after spectrograms.

**J. Experimental metrics.** Measured frequency response per band (compare hardware output against your Python-designed target response); frequency response flatness at unity gain; FPGA resource utilization vs. number of bands/filter order (a nice quantitative "design space" result — plot resource usage vs. N); latency through the filter bank.

**K. Literature.**
1. Any standard digital filter design reference (e.g., Oppenheim & Schafer, *Discrete-Time Signal Processing,* filter design chapters) — this project is closer to a "textbook DSP building block, done in hardware" than a single novel research result, so a strong textbook + the LMS/FIR FPGA papers already cited in Project 2 (sources 2–5 there) for the *hardware implementation methodology* (fixed-point FIR design, Vivado/Verilog structuring) apply directly here too, since a static-coefficient FIR bank is a simpler special case of the adaptive filter those papers implement.
2. "FPGA Implementation of LMS-based FIR Adaptive Filter for Real Time Digital Signal Processing Applications" — (cite index="52-1">discusses fixed-point arithmetic representation for an FPGA-based adaptive filter system, synthesized and simulated in Xilinx tools, and reports on hardware resource usage and power consumption tradeoffs</cite> — directly useful for FIR-on-FPGA implementation methodology even though your filters are static, not adaptive.

**L. Replication possibility.** This project is intentionally the "safe" option — there isn't a specific paper result to replicate line-for-line so much as a design methodology (filter bank design + FPGA FIR implementation) to apply correctly. For the mid-term report, "replication" here means: design your filter bank in Python, verify its frequency response matches your target specification (a flat filter bank sum), and cite the FIR-on-FPGA implementation approach from the sources above as your methodological basis.

**M. Extensions.**
1. Increase band count and add a real-time bar-graph "spectrum analyzer" style LED visualization of per-band energy.
2. Add a simple FFT-based analyzer alongside the filter bank for a direct frequency-domain vs. time-domain-filtering comparison (ties in FFT, a core course topic, as a genuine extension rather than a bolt-on).
3. Make filter cutoffs themselves user-adjustable (not just gains) via switches, requiring either a small bank of pre-computed coefficient sets or on-the-fly coefficient recomputation.
4. Add a simple audio effect (e.g., basic reverb via a delay line, or a compressor/limiter) as a second processing stage after the EQ.

**N. Team-of-4 distribution.**
- *Member 1:* Filter design methodology (frequency-response specs, order selection), literature/report writing.
- *Member 2:* Python simulation, frequency-response verification, all report plots.
- *Member 3:* Verilog RTL for the filter bank + gain/sum logic, testbenches.
- *Member 4:* Fixed-point verification, Pmod audio front-end + switch-control integration, hardware testing and demo polish.

**O. Expected difficulty: Beginner-friendly.** No adaptive logic, no nonlinear operations, generous resource margins, and an extremely well-documented design methodology — the main risk is scope creep (adding too many bands/effects), not a fundamental hardware barrier.

**P. Time feasibility.**
- Literature/filter-design study: 1 week
- Python filter design + verification: 1.5 weeks
- Verilog implementation: 1.5–2 weeks
- Hardware integration + testing: 1 week
- Extensions (if time allows): 1–2 weeks
- Report/presentation: ongoing + 1 week
- **Flag:** because this project is comparatively easy, the main risk is *not enough depth* for a full-semester grade — plan at least one extension (spectrum visualizer or FFT comparison) as a firm target, not an optional stretch goal, so the final deliverable has enough substance.
