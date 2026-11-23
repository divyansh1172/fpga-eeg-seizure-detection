# EE2000 Signal Processing — Boolean Board Project Research Report

**IIT Hyderabad, Fall 2026 | Prepared for a 4-member team**

---

## 1. Executive Summary

This report is structured exactly as requested: flier requirements first, then verified Boolean Board hardware capabilities, then literature-backed project ideas, a comparison table, a shortlist, deep dives, a development roadmap, and a sourced bibliography.

**Key finding that shapes everything below:** the Boolean Board has **no onboard microphone, no onboard audio-in, no onboard general-purpose DAC, and no camera interface.** It has an HDMI *output*, a single-channel onboard ADC wired to a thumbwheel potentiometer, 16 auxiliary XADC channels reachable through the Pmod headers if *you* wire something to them, and PWM-only audio *output* through a filtered 3.5mm jack. This means every audio-input, ECG-input, or camera-input project in this report requires an external Pmod module (a few hundred to a few thousand rupees) — there is no way around this with onboard hardware alone. Image and communications-signal projects can be done **entirely without external hardware** by storing test data in on-chip BRAM and driving the HDMI output, which is a legitimate and common way to demonstrate FPGA signal processing without needing a live sensor.

Given your team is comfortable with FPGA work and open to buying modules, the full range of ideas below is realistic. I've marked exactly which external module each idea needs and given approximate costs.

---

## 2. Project Flier Requirements (extracted directly from the PDF)

Only what is stated in the flier — nothing invented:

- **Teams:** 4 members, team-deadline 05.09.2026. Grades are team-wide.
- **Preliminary report — 27.09.2026 (5%).** Must include a clearly identified problem statement and a summary of related literature reviewed. Must use the **IEEE CVF Conference template** (linked in the flier).
- **Mid-term report — 25.10.2026 (5%).** Must include: further literature review, results replicated from the literature, and preliminary results from your own work. Any code developed/experimented with must be submitted.
- **Final report — 13.11.2026 (5%, report + results + code).** Must build on prior reports and present your algorithm, results, and conclusions. Code must be submitted. **Each team member's individual contribution must be clearly delineated, and their code appropriately commented.**
- **Project presentation and viva (date TBD, 5%).** The team must present their work **on the Boolean Board** and answer questions.
- **AI usage policy:** AI tools (ChatGPT, Claude, etc.) are explicitly permitted, but AI-generated parts of the work must be clearly indicated and cited, and the team must be able to explain and defend any AI-generated content during the viva. *(This report itself, and any content from it you use, falls under this policy — cite it and be prepared to explain the hardware facts and literature claims independently.)*
- **Suggested topic areas** (non-exhaustive, per flier): biomedical (ECG/EEG/EMG), audio/speech (speech enhancement, music source separation), image/video (denoising, super-resolution), communications (channel equalization, MIMO detection), and "current trends in machine learning for signal processing."

**Not stated in the flier (so not assumed below):** page limits, grading rubric weightings within each report, whether external hardware purchases are funded or reimbursed, specific citation format beyond "appropriate citations," and the exact viva format. **You should confirm these with your instructor/TA** — I've flagged this again in Section 13.

---

## 3. Xilinx Boolean Board — Verified Capabilities

Source: official Real Digital documentation and datasheet (full links in Section 12). Every claim below is traceable to a specific source; where I could not verify something, I say so explicitly.

| Item | Verified fact | Source |
|---|---|---|
| FPGA | Xilinx (AMD) **Spartan-7 XC7S50** | Real Digital datasheet |
| Logic capacity | >8,000 slices (4× 6-input LUTs + 8 flip-flops each) ≈ **52K logic cells** | Real Digital datasheet |
| DSP resources | **120 DSP48 blocks**, each with dual 24-bit adders, a 2's-complement multiplier, 48-bit accumulator | Real Digital datasheet |
| On-chip RAM | **337 KB** dual-port high-speed BRAM | Real Digital datasheet |
| Clocking | 5 Clock Management Tiles (MMCM/PLL), generate multiple clocks from one external source | Real Digital datasheet |
| ADC | **On-board 12-bit, 1 MSPS XADC**, wired by default to a **thumbwheel potentiometer** on the board | Real Digital datasheet + product page |
| Auxiliary analog inputs | The Spartan-7 XADC primitive supports **16 auxiliary differential analog input pairs (VAUXP/VAUXN)** in addition to 1 dedicated pair — accessible only if you route external signals to the right Pmod-header pins yourself; 1V peak-to-peak limit in analog mode | Xilinx UG480 (XADC User Guide) |
| DAC | **No general-purpose DAC.** Audio "out" is PWM/PDM-based (see below), not a true DAC | Real Digital documentation |
| Audio | **Two on-board audio amplifier/filter circuits** (50 Hz–5 kHz bandpass, AC-coupled) driving a 3.5 mm stereo jack, designed to take **PWM/PDM square-wave signals from the FPGA and turn them into audio** — this is **output only**. There is **no on-board microphone or audio line-in** | Real Digital documentation |
| Video | **HDMI output, 1080p.** No HDMI input, no camera connector | Real Digital datasheet |
| GPIO/expansion | Two 30-pin expansion connectors (4 Pmod-compatible ports total), 22 FPGA I/O signals per connector routed as differential pairs, plus header J1/J2 carry 12 extra GPIO between the Pmod ports | Real Digital reference manual + community board files (GitHub: proto17/RealDigital_BooleanBoard) |
| Switches/buttons | 16 slide switches, 5 push-buttons | Real Digital datasheet |
| LEDs | 16 discrete LEDs, 2 RGB LEDs | Real Digital datasheet |
| 7-segment display | Two 4-digit common-anode modules = 8 digits total | Real Digital documentation |
| Servo outputs | 4 servo connectors (standard PWM servo protocol) | Real Digital datasheet |
| Storage | QSPI flash for configuration + user data | Real Digital datasheet |
| Wireless | Optional on-board Bluetooth Low Energy radio | Real Digital datasheet |
| Serial | USB (power, programming, UART/COM) via single USB cable | Real Digital documentation |
| Toolchain | **Xilinx/AMD Vivado (Webpack, free).** Full Verilog and VHDL support, simulator, synthesizer, programmer, integrated logic analyzer | Real Digital documentation |
| Device part number (for Vivado project settings) | `xc7s50csga342-1` | Xilinx University Program Vivado flow guide |

### 3.1 What I could NOT verify

- The exact **maximum achievable system clock frequency** for a typical student design (this depends heavily on your specific design's critical path, not a single fixed number — the FPGA's fabric supports well over 100 MHz for simple designs, but I found no official "rated max frequency for student projects" figure, and quoting one would be fabricating precision that doesn't exist).
- Whether IIT Hyderabad's specific lab kit includes any **bundled Pmod modules** beyond the base board — you should check with your TA/lab manual, since if a mic or ECG-front-end Pmod is already provided, that changes your external-hardware calculus for free.
- Exact current retail price/availability of Boolean Boards or specific Pmods **in India** (I found US list prices only; Indian distributor pricing and import lead time should be checked directly, e.g. via IIT Hyderabad's procurement or a local Digilent reseller).

### 3.2 A. Directly possible on the Boolean Board (no external hardware)

- Any purely digital algorithm operating on **pre-stored or synthetically generated data** (FIR/IIR filters, FFT, correlation, convolution) with results shown on 7-segment displays, LEDs, UART to a PC terminal, or an HDMI-driven on-screen display/plot.
- **Image processing** on a **static test image stored in BRAM** (via a `.coe`/`.mem` file generated offline from a PNG/JPEG), processed by the FPGA, and displayed live over HDMI. This is a well-established educational pattern (see Section 5, Project 4) and needs zero external hardware.
- **Digital communications** (BPSK/QPSK modulation, matched filtering, symbol detection, BER computation) using an **on-chip AWGN generator** (e.g. LFSR + Box-Muller approximation) — fully self-contained on the FPGA, no external RF hardware needed.
- **PWM-based audio output** of a processed/synthesized signal, out the 3.5 mm jack, if your project's *output* (not input) is audio.
- Using the **thumbwheel-pot ADC channel** as a single slow-varying analog input (e.g., a user-adjustable parameter, not a real signal source — 1 channel, not designed for waveform capture from an external source).

### 3.3 B. Requires an external peripheral

- **Any real audio input** (speech, ambient noise, music) → needs a Pmod microphone or a Pmod ADC + external mic circuit, since there is no on-board mic or audio line-in.
- **Any real ECG/EMG/EEG input** → needs a biopotential front-end module (e.g. an AD8232-based ECG breakout) wired into a Pmod header via the auxiliary XADC pins, or a dedicated Pmod-format ADC.
- **Live camera-based image input** → needs a Pmod or breakout camera module (e.g. an OV7670-class module) — HDMI is output-only.
- **True analog waveform output** (e.g., reconstructing a smooth analog signal rather than PWM audio) → needs a Pmod DAC (e.g. PmodDA1, SPI-driven).
- **Multi-channel simultaneous analog acquisition** (e.g. 2-lead ECG, stereo audio) → needs a 2-channel+ Pmod ADC.

### 3.4 C. Impractical for this project

- Anything requiring **>52K logic cells or heavy floating-point pipelines** at scale (e.g., a full-precision deep CNN with millions of parameters) — 120 DSP48 slices and 337 KB BRAM is enough for a small quantized/binarized network or a handful of parallel filter taps, not a modern-scale neural net.
- **High-sample-rate RF/SDR work** (e.g., real GHz-band signal capture) — there is no RF front-end on this board; anything "wireless" here must be a **baseband/simulated-channel** demonstration, not literal over-the-air RF.
- **Video input processing in real time from a live camera at high resolution** — feasible in principle with an external camera Pmod, but buffering a full frame in only 337 KB of BRAM is tight (a single 320×240 8-bit grayscale frame alone is ~75 KB, so this is workable at QVGA/grayscale but not at full HD/color without external SRAM — flagged as a real risk in Section 9).
