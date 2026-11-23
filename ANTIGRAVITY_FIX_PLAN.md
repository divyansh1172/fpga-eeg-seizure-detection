# EE2000 Seizure Detector – Antigravity Fix Plan

Project: EEG seizure detection on RealDigital Boolean Board (Spartan-7 XC7S50, 100 MHz)
Pipeline: UART RX → IIR biquad → db4 DWT → feature accumulator → linear SVM → alarm → display

**How to use this file:** put it in the repo root next to the `.v` / `.xdc` files. Tell Antigravity:
*"Read ANTIGRAVITY_FIX_PLAN.md. Execute one task at a time, in order. Stop and wait for my approval after each task."*

---

## 0. Global rules (apply to every task)

- Verilog-2001, synthesizable, Vivado. Target `xc7s50csga324-1`, 100 MHz.
- Work on **one module per task**. Do not edit other files unless the task says so.
- Every change needs a **self-checking testbench** and a **Python golden model** (numpy/scipy/pywt). Run the simulation and paste the real log. Never claim "passes" without running it.
- Keep module ports stable unless the task allows a change. List every port change explicitly.
- No async reset on RAM-style arrays (prevents BRAM/LUTRAM inference). Use RAM for per-channel state.
- Resource budget: 120 DSP48E1. Samples arrive once per ~4340 clocks (230400 baud, 4 bytes/sample), so use a **time-multiplexed datapath with per-channel state in RAM**, not 22 copies of hardware.
- The existing code is AI-scaffolded and **contains bugs. Do not trust it or its comments.** Trust only tests.
- After every task output: (1) summary, (2) diff, (3) sim log, (4) remaining risks. Then commit to git with message `task-N: <name>`.

### Fixed system facts
| Item | Value |
|---|---|
| Channels | 22, round-robin interleaved (ch0…ch21) |
| Sample rate | 256 Hz per channel |
| Packet | `0xAA`, `ch_id`, `MSB`, `LSB` (16-bit signed, big-endian) |
| UART | 230400 baud, 8N1, 434 clk/bit |
| Window / hop | 1 s non-overlapping, 256 frames |
| Subbands | D3, D4, D5, A5 (levels 3, 4, 5 of db4 DWT) |
| Features | 22 ch × 4 bands × 2 (energy, line-length) = 176 |
| Persistence k | sw[1:0] → 1, 2, 3, 5 |

---

## 1. Known issues (source of truth for this plan)

### Critical
| ID | File | Issue |
|---|---|---|
| C1 | `iir_biquad.v`, `dwt_db4.v` | One shared filter state for 22 interleaved channels → every channel's history is corrupted by its neighbours. Needs per-channel state. |
| C2 | `dwt_db4.v` | `decimate_phase` toggles globally; 22 is even → same channels always hit the compute phase; ~11 channels never produce output. |
| C3 | `dwt_db4.v`, top | Only a level-1 DWT exists; top claims 5-level. `curr_subband` is a free-running 0..3 counter; `dwt_detail` is fed to all 4 "subbands"; `dwt_approx` is unused. |
| C4 | `dwt_db4.v` | `approx_out/detail_out <= sum_*` reads the previous registered sum → output is stale by one decimation period. |
| C5 | top | `seizure_alarm_latched` never clears (btn unused). `uart_txd` driven to 0 forever after first alarm (permanent UART break). |
| C6 | top | `latched_latency <= 16'd8` is hard-coded, not measured. |
| C7 | top, `svm_classifier.v` | SVM weight ROM is a dummy pattern; bias (16-bit, −6627) not in the scale of `feat × weight` products. |

### Serious
| ID | File | Issue |
|---|---|---|
| S1 | `iir_biquad.v` | Both biquad sections + saturation in one combinational cycle → will fail 100 MHz timing. |
| S2 | `iir_biquad.v` | `>>> 20` before storing state discards all fractional bits; SQNR claim (>80 dB) is false; truncation bias amplified by 0.5 Hz HP pole (0.9828). |
| S3 | `feature_accumulator.v` | Sample arriving in same cycle as `window_sync` is dropped; `hop_sync` fires on ch21's last sample but its filtered coefficient lands in the next window. |
| S4 | `feature_accumulator.v` | `normalize_energy` returns 14-bit `acc[34:21]`, not 19-bit; bits [37:35] discarded, no saturation. `Nb` (64/32/16) assumes 64 D3 coeffs/window but 1 s @ 256 Hz gives 32 at level 3. Recheck all shifts. |
| S5 | `feature_accumulator.v` | Line-length acc 23-bit overflows beyond 64 samples of max diff; `diff_val` 16-bit can overflow (17-bit diff), `-(-32768)` overflows. |
| S6 | `dwt_db4.v` | Comment says "with saturation" but `sum[30:15]` just wraps. Tap-sum ≈ 1.9 so overflow is reachable. |

### Minor
| ID | File | Issue |
|---|---|---|
| M1 | `uart_rx.v` | No stop-bit check / framing error. Packet FSM has no checksum; `0xAA` can appear in payload. Bandwidth use is 97.8% (225,280 / 230,400 bps), almost no slack. |
| M2 | top | `rst` described as synchronous but used as raw async reset from an un-debounced button. Add reset synchronizer. |
| M3 | `alarm_logic.v` | Never instantiated; top duplicates logic inline (with refractory that the module lacks). |
| M4 | `iir_biquad.v` | `reset_state` tied to same `rst` as `rst_n` (redundant). |
| M5 | `dwt_db4.v` | `H2` = 0x50C2 (20674) should be 20673; `H5` = 0x03F1 (1009) should be 1011. `G` is negated vs. its comment formula (harmless for energy / line-length). Taps are pywt *reconstruction* order (time-reversed, same magnitude). |
| M6 | `seven_seg_controller.v` | Per-digit pin comments disagree with the XDC (e.g. `anode[7]`=E4 in XDC, "Pin J4" in comment). |
| M7 | top | `strobe_cnt[23]` ≈ 6 Hz (comment says ~4 Hz). `rgb0_g` is always on, not a "streaming OK" indicator. |
| M8 | `feature_accumulator.v` | Async-reset loops on big arrays → ~10k flops + huge muxes instead of RAM. |
| M9 | `boolean_board.xdc` | No duplicate pins, but "verified against official pinout" is unverified. **Do not let the agent verify this from memory.** User cross-checks against RealDigital's master XDC. |

---

## 2. Phase 0: Confirm understanding (no code)

**Prompt to paste:**
```
Read ANTIGRAVITY_FIX_PLAN.md and all attached .v / .xdc files. Do NOT write code yet.
1. Restate the architecture and data flow in your own words.
2. For each issue C1..M9, confirm it by pointing at the exact lines, or tell me you disagree and why.
3. Propose the per-channel state memory layout for IIR and DWT (depth, width, RAM type).
4. Propose the interface for the new multi-level DWT (ports, valid signals, channel tagging).
Wait for my approval.
```
**Gate:** user approves architecture and interfaces.

---

## 3. Phase 1: Golden model (before any RTL)

**Deliverable:** `golden/golden.py`

**Prompt:**
```
Write golden/golden.py implementing the full chain on a 22-channel interleaved int16 stream:
- causal 4th-order Butterworth bandpass 0.5-25 Hz @ 256 Hz (two biquad sections; use the
  coefficients in iir_biquad.v, and also a float reference via scipy for comparison)
- causal 5-level db4 DWT (use pywt dec_lo/dec_hi, decimate by 2 per level)
- D3, D4, D5, A5 sub-bands per channel
- per 1 s window: energy and line-length per (channel, subband)
- 176-dim feature vector, dot product with a weights file, bias, sign decision
- k-consecutive persistence + 30 s refractory alarm model
Also provide a fixed-point mode that mirrors the intended RTL arithmetic (bit widths and shifts
as parameters). Dump per-stage .hex/.mem vectors into golden/vectors/ for testbenches.
Include a README with how to run it. Show me the output on a synthetic test signal.
```
**Gate:** golden float vs. fixed-point error is reported and acceptable; features match what's already in the team's report.

---

## 4. Phase 2: Fix tasks (strict order)

### Task 1: UART RX and packet framing (M1)
**Files:** `uart_rx.v`, packet FSM section of `top_seizure_detector.v`
**Do:**
- Check stop bit; add `frame_err` output; on error return to IDLE without asserting `byte_valid`.
- Packet FSM: resync robustly. Propose a lightweight integrity check (e.g. ch_id range check plus optional 5th checksum byte, only if the host script can be changed. Otherwise a sync-validation heuristic) and document the trade-off.
- Add a `dropped_frame` / `err_count` counter visible for debug.

**Testbench:** UART bit-banger TB sending (a) normal stream at 97.8% duty, (b) payload bytes equal to `0xAA`, (c) dropped byte mid-packet, (d) glitch/false start bit.
**Acceptance:** no lost valid frames in (a); FSM re-locks within 2 packets in (b)-(d); sim log shows counts.

**Prompt:**
```
Task 1 from ANTIGRAVITY_FIX_PLAN.md. Only touch uart_rx.v and the packet FSM in the top.
Implement the changes, write tb_uart_rx.v and tb_packet_fsm.v, run them, and show the logs.
```

### Task 2: IIR biquad, per-channel and pipelined (C1, S1, S2, M4)
**File:** `iir_biquad.v`
**Do:**
- Add `ch_in[4:0]` / `ch_out[4:0]` ports. Store x1, x2, y1, y2 for both sections in RAM indexed by channel (22 entries).
- Keep **fractional guard bits** in stored state (e.g. Q12 or more); only round/saturate at the final 16-bit output. Use round-to-nearest, not truncation.
- Replace the combinational chain with a serial MAC (or ≥3 pipeline stages). Latency is irrelevant (≈4000 idle clocks per sample).
- Remove redundant `reset_state`, or give it a real per-record purpose that clears all channel state.
- Re-derive coefficient quantization (e.g. `b1`=131377, `a1h`=-2078976) and document the error.

**Testbench:** interleaved 22-channel stimulus with different tones per channel; compare each channel to golden.
**Acceptance:** each channel matches golden within ±1 LSB (16-bit output); WNS ≥ 0 at 100 MHz in an out-of-context synth; no channel crosstalk (inject tone on only ch5, others stay at zero).

**Prompt:**
```
Task 2 from ANTIGRAVITY_FIX_PLAN.md. Only touch iir_biquad.v. Per-channel RAM state, guard bits,
pipelined or serial MAC. Write tb_iir.v using golden/vectors. Report max abs error per channel,
and run Vivado out-of-context synthesis at 100 MHz and report WNS, DSP, LUT, FF counts.
```

### Task 3: Multi-level db4 DWT (C1, C2, C3, C4, S6, M5)
**File:** `dwt_db4.v` (may split into `dwt_level.v` + `dwt_db4_cascade.v`)
**Do:**
- Cascade 5 levels. Each level: per-channel shift registers and per-channel decimation phase, stored in RAM.
- Level n's approximation feeds level n+1. Output tagged with `ch_out` and one-hot `valid_d3 / valid_d4 / valid_d5 / valid_a5` (detail of levels 3, 4, 5 and approximation of level 5).
- Align compute and output (fix stale-output bug): `out_valid` must accompany the data computed from the same samples.
- Saturate on the Q15 rescale.
- Use correct pywt **decomposition** filter taps (`dec_lo` / `dec_hi`) with exact rounding; fix `H2` / `H5`; make the G-vs-comment sign consistent.
- Decimation phase must be **per channel**, not global (fixes C2).

**Testbench:** impulse, step, chirp, and real EEG segment on all 22 channels.
**Acceptance:** all 22 channels produce outputs at the expected rate (D3: 32/s, D4: 16/s, D5: 8/s, A5: 8/s per channel); matches pywt-based golden within ±1 LSB at each level; overflow test shows saturation, not wrap.

**Prompt:**
```
Task 3 from ANTIGRAVITY_FIX_PLAN.md. Rewrite the DWT as a 5-level per-channel cascade with tagged,
one-hot valid outputs for D3, D4, D5, A5. Fix the stale-output bug and the global decimation phase.
Verify against pywt via golden/vectors. Show per-level and per-channel output counts per second.
```

### Task 4: Feature accumulator (S3, S4, S5, M8, C3)
**File:** `feature_accumulator.v` (+ the subband-router part of top)
**Do:**
- Remove `curr_subband` counter from top. Accumulator takes `ch_id` and the one-hot valids (or a decoded `subband_id` produced by the DWT).
- Eliminate the window race: double-buffer accumulators (ping-pong) or delay latch until the pipeline has drained; no coefficient may be lost or counted in the wrong window.
- Recompute normalization shifts from the **actual** coefficient count per window per band; produce a 19-bit saturating energy feature. Document the math.
- Widen line-length accumulator and difference arithmetic (17-bit diff, safe abs); define the scaling to a 19-bit feature.
- Infer RAM for accumulators/latches (no async-reset loops over arrays; use a sequential clear sweep).
- Keep the serial streaming interface (`feat_stream_start`, `feat_index`, `feat_data`) alignment unchanged so the SVM timing still works. Verify alignment explicitly.

**Testbench:** full-window replay from golden vectors for all 176 features; plus stress for the boundary race (coefficient on the exact `window_sync` cycle).
**Acceptance:** 176/176 features match golden within defined tolerance; no coefficient loss in the race test.

**Prompt:**
```
Task 4 from ANTIGRAVITY_FIX_PLAN.md. Fix feature_accumulator.v and remove curr_subband from the top.
Double-buffer or drain to remove the window race, recompute normalization from real coefficient
counts, widen line-length, infer RAM. Test against golden features and a boundary-race stress test.
```

### Task 5: SVM and weights (C7)
**Files:** `svm_classifier.v`, weight ROM in top, new `tools/export_svm.py`
**Do:**
- `tools/export_svm.py` converts the trained model (weights + bias) to quantized `weights.mem` (and bias), with chosen Q-formats, and reports quantization error on the validation set.
- Top loads ROM via `$readmemh("weights.mem")` (or BRAM init). Remove the dummy pattern.
- Bias width/scale must match the `feat × weight` product scale (use a wider bias input, e.g. 32 bits).
- Keep the 176-cycle serial MAC and the one-cycle `done` pulse. Clean the redundant `FEAT_DIM <= 1` branches.

**Acceptance:** RTL score matches Python float score within quantization bound on ≥ 100 windows; decision agreement ≥ 99.9% except near-zero scores (list the exceptions).

**Prompt:**
```
Task 5 from ANTIGRAVITY_FIX_PLAN.md. Add tools/export_svm.py (I will supply model weights as
weights.npy / bias.npy), load via $readmemh, widen the bias path, and test RTL vs Python scores.
If model files are missing, STOP and ask me, do not invent weights.
```

### Task 6: Alarm, TX and display behaviour (C5, C6, M3, M7)
**Files:** alarm section of top (or instantiate a fixed `alarm_logic.v`), `seven_seg_controller.v`
**Do:**
- Put alarm/persistence/refractory in **one** module (fix and instantiate `alarm_logic.v` with sw-selectable k and 30 s refractory; delete duplicate inline logic).
- Add alarm clear on `btn[1]` (debounced, edge-detected). Define behaviour: clear latch and counters, keep refractory or not (document the choice).
- Replace the `uart_txd` abuse: either tie it to idle-high and drop it, or implement a small real `uart_tx` sending one status byte per alarm.
- Latency: remove the hard-coded 8. Either measure from a host-supplied onset marker (define the protocol) or remove it from the display. Ask the user which.
- Fix `rgb0_g` to a real "streaming OK" (e.g. valid frames seen in the last second). Fix strobe comment (≈6 Hz).
- Fix the per-digit pin comments in `seven_seg_controller.v` to match the XDC.

**Testbench:** alarm sequences for k=1,2,3,5, refractory, clear, back-to-back positives.
**Acceptance:** sim log shows the expected alarm count for each scenario.

**Prompt:**
```
Task 6 from ANTIGRAVITY_FIX_PLAN.md. Merge alarm logic into one module with k from sw[1:0],
30 s refractory, and btn[1] clear. Remove the hard-coded latency: ASK me which option I want
before implementing. Replace the stuck-low uart_txd. Add tb_alarm.v and show the logs.
```

### Task 7: Reset, cleanup, lint (M2, M5, M6, M7)
**Do:**
- 2-flop reset synchronizer (async assert, sync deassert) plus a debounce on the reset button; distribute the synchronized `rst_n`.
- Clean unused ports/warnings; run Verilator `--lint-only -Wall` (or Vivado lint) and fix real warnings.
- Update header comments so they match the actual behaviour.

**Acceptance:** lint is clean (or every remaining warning is justified); the full TB still passes.

---

## 5. Phase 3: Integration and implementation

1. **System testbench** `tb_top.v`: replay a real CHB-MIT segment through the UART bit-banger (including a seizure segment); compare per-window decisions and alarm times to golden.
2. **Vivado synth + impl** with the XDC; report WNS/TNS/WHS, LUT/FF/BRAM/DSP utilisation. Fix negative slack by **pipelining, not by lowering the clock**.
3. **Regression script** `run_all.sh` that runs every testbench plus golden comparison and prints a PASS/FAIL table.
4. **XDC check (user does this):** diff `boolean_board.xdc` against RealDigital's official master XDC (UART, RGB, anode order, button pins). The agent must not self-certify pins.
5. Update the project report numbers (resource usage, latency, SQNR) from the new measured results; do not reuse the old claimed figures (e.g. ">80 dB SQNR") unless re-measured.

**Prompt:**
```
Phase 3 from ANTIGRAVITY_FIX_PLAN.md. Build tb_top.v with real EEG vectors through the UART model,
write run_all.sh, run Vivado synth+impl, and give me a table of WNS, utilization, and
RTL-vs-golden decision agreement. List anything still failing.
```

---

## 6. Rules of engagement for the agent

- If a task needs info you don't have (model weights, host script protocol, latency definition), **stop and ask**; never invent it.
- Do not "fix" things by loosening a testbench tolerance without telling me.
- If you disagree with an issue in section 1, say so with evidence (a simulation, not opinion).
- One task → one commit → wait for approval.
- Keep a `CHANGELOG.md` with per-task notes and measured numbers.

## 7. Final checklist

- [ ] Golden model done and agrees with report features
- [ ] T1 UART/framing
- [ ] T2 IIR per-channel and timing met
- [ ] T3 5-level DWT, all 22 channels live
- [ ] T4 Features match golden, race fixed
- [ ] T5 SVM with real weights
- [ ] T6 Alarm / clear / TX / display
- [ ] T7 Reset and lint
- [ ] System TB passes on real CHB-MIT data
- [ ] Vivado WNS ≥ 0 at 100 MHz
- [ ] XDC manually checked against the official file
- [ ] Report numbers updated from measured results
