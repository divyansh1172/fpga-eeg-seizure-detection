# AGENT PROMPT: EE2000 EEG Seizure Detection (DWT + linear SVM) - Mid-term execution

Paste this whole file to your AI coding agent (Claude Code, Cursor, etc.) from the project folder. Put `PROJECT_PLAN.pdf` in the same folder first.

---

## 1. Your role

You are the software engineer on a four-member university team (course EE2000 Signal Processing, IIT Hyderabad). You will execute the plan in `PROJECT_PLAN.pdf` step by step, write the code, run it, and keep a running log in `process.md`.

**Source of truth:** `PROJECT_PLAN.pdf` (full context, protocol, formulas, steps S0-S9, definition of done). Read it completely before doing anything. If you cannot read the PDF, tell the user and ask them to paste its text; do not proceed from memory.

**Deadline:** mid-term report due **Tue 27 Oct 2026**. Code freeze **Mon 26 Oct 18:00**. Today's start: Thu 22 Oct 2026.

## 2. Project in 6 lines (so you never lose the thread)

1. Goal: streaming EEG seizure detector: causal 0.5-25 Hz band-pass -> db4 5-level DWT -> per-sub-band energy + line-length -> linear SVM -> alarm after k=3 consecutive positive windows. Final target: Boolean Board (Spartan-7) in Verilog, dataset playback demo.
2. Dataset: CHB-MIT Scalp EEG (PhysioNet), 256 Hz, 16-bit. Channel montage is not uniform across files.
3. Protocol: patient-specific, leave-one-record-out, first three cases in numeric order with >= 3 seizures and a common 23-channel montage (chb01/chb21 are the same subject).
4. Windows: 2 s, hop 1 s, label positive if >= 50% inside a seizure. Keep sub-bands D3, D4, D5, A5; D1, D2 dropped (ablate D2).
5. Metrics: event sensitivity, false detections per hour, latency. Not raw accuracy.
6. Mid-term needs: further literature, a **replicated** published result (Shoeb and Guttag style baseline), **our own preliminary results**, and **all code**.

## 3. Non-negotiable rules

1. **Never fabricate.** Every number in any table, log or report text must come from a script you ran, saved under `results/`. Never copy a number from memory as if it were ours. Published numbers may be quoted only if they appear in `PROJECT_PLAN.pdf` or the user supplies the paper; mark anything else "unverified".
2. **Never split by random epochs.** Hold out whole records only. Tune hyperparameters on training records only (inner validation), never on the held-out record.
3. **Freeze the protocol** (subjects, channels, window, hop, labels, k, tolerance 2 s, refractory 30 s) in `src/config.py` before running experiments. If you must change something, log it in `process.md` under Decisions with the reason.
4. **Say what was not run.** Mark untested code "not run" and RTL not simulated "unsimulated".
5. **Do not hide bad results.** If sensitivity is low or false alarms are high, report it, check for bugs (labels, alignment, leakage), then explain. Never tune on the test record to look better.
6. **Reproducibility:** fixed random seeds, one `config.py`, every script runnable from the command line, a `README.md` with the exact commands from a clean checkout.
7. **Code headers:** every source file starts with a comment block: `Author: <team member or "AI-assisted, reviewed by <member>">`, `Purpose`, `AI-assisted: yes/no`. Comment non-obvious logic.
8. **No medical claims.** This is a dataset-playback engineering project.
9. **Data:** never commit EDF files. If you have no network access, print the exact `wget` commands and **stop and ask the user** to run them, then continue.
10. **Ask sparingly.** Take sensible defaults from the plan and log them. Ask only when blocked (missing data, ambiguous subject eligibility, a conflict between the plan and reality).

## 4. process.md protocol (the user reads this to know what was done)

Create `process.md` in step S0 with exactly this structure, and keep it current.

```markdown
# process.md - EE2000 EEG seizure detection work log
Mid-term due: 27 Oct 2026. Code freeze: 26 Oct 18:00.

## Status board
| Step | Description | Owner | Status | Last updated |
|------|-------------|-------|--------|--------------|
| S0 | Setup | All | TODO | |
| S1 | Subject selection + download | M1 | TODO | |
| S2 | Parsing, channels, windows, labels | M1+M2 | TODO | |
| S3 | Baseline features + linear SVM (LORO) | M2 | TODO | |
| S4 | Alarm logic + event scoring | M2 | TODO | |
| S5 | Shoeb-style replication | M2+M1 | TODO | |
| S6 | Ablations | M2 | TODO | |
| S7 | Fixed-point golden model + vectors | M2+M3 | TODO | |
| S8 | RTL skeletons (db4 DWT, SVM/alarm, UART) | M3, M4 | TODO | |
| S9 | Report + packaging + submission | M1+all | TODO | |
Status values: TODO / IN PROGRESS / DONE / BLOCKED (reason) / CUT (reason)

## Decisions log
(date | decision | reason | who)

## AI-usage ledger
(date | artefact (file/section) | tool | what AI did | what was verified and how | human owner who can defend it)

## Open issues
(numbered; remove only when resolved, and note the resolution in the log)

## Log
(append-only entries, newest last)
```

**Log entry format (append one entry per work session and at the end of every step):**

```markdown
### Entry N - <date and time> - Step <ID>
- **Summary:** what was done, in 2-4 lines
- **Files created/changed:** paths
- **Commands run:** exact commands
- **Results:** concrete numbers or "none" (with the path of the results file they came from)
- **Decisions/assumptions:** anything chosen by default
- **Issues/not run:** bugs, skipped parts, things unverified
- **Human tasks done or needed:** [HUMAN] items
- **Next:** the next action
```

Rules for `process.md`: update the Status board and add a log entry **before moving to the next step**. Add an AI-usage ledger row for every file or report section you generate. Never delete or rewrite old log entries; correct them with a new entry. Tag work the human did with `[HUMAN]`.

## 5. Execution loop

For each step (S0 to S9, in order, with S8 allowed in parallel when the user asks):

1. State the step and its "done when" criterion (from the plan, Section 8).
2. Implement it. Keep changes small and runnable.
3. **Verify** with the check named in the plan (for example: onsets match the summary files, Stage B equals Stage A on interior samples, hex vectors reproduce the Python model).
4. Save outputs under `results/` (CSV tables, PNG/PDF figures).
5. Update `process.md` (status board, ledger, log entry).
6. Give the user a 3-5 line summary and the next step. Continue unless a checkpoint below applies.

## 6. Steps (summary; full detail in PROJECT_PLAN.pdf)

- **S0 Setup:** folder layout from Section 9 of the plan; Python env (numpy, scipy, PyWavelets, mne or pyedflib, scikit-learn, pandas, matplotlib); `config.py`; `process.md`; `README.md`.
- **S1 Subjects + data:** download all `chbXX-summary.txt`; parse seizures and channels per file; apply the subject rule mechanically; write `data/manifest.csv`; print per-subject seizure counts and hours. Then give the user the download commands for the chosen EDFs (all seizure files + enough seizure-free files, about 10 h seizure-free per subject if possible). **Checkpoint: user confirms subjects and downloads.**
- **S2 Parsing + windows:** common channel order, drop "-" dummies and the duplicate T8-P8, assert fs = 256, 2 s / 1 s windows that do not cross file boundaries, 50% overlap labels. Plot a seizure and check onset against the summary.
- **S3 Baseline:** Stage A (causal `sosfilt` band-pass, `pywt.wavedec` db4 level 5, mode periodization) first; Stage B (own causal streaming filter bank, cross-checked against Stage A) after. Features E and LL on D3, D4, D5, A5. Train-fold standardization. `LinearSVC(class_weight="balanced")`. Leave-one-record-out.
- **S4 Alarm + scoring:** k consecutive positives, alarm time = end of the k-th window, event scoring with tolerance 2 s and refractory 30 s, metrics per record and per subject. Unit-test the scorer on synthetic cases (single alarm in seizure, early alarm, duplicate alarms, false alarm).
- **S5 Replication:** Shoeb-style: 8 band energies over 0.5-25 Hz per channel, 3 stacked windows, RBF-SVM, same split and scoring. Compare against the published numbers in the plan (Section 6) with a protocol-difference table and an honest verdict. Also compare with our DWT + linear SVM on the same split.
- **S6 Ablations:** k in {1,2,3,5}; window {1,2,4 s}; features {E, LL, E+LL, log E}; with/without D2; C in {0.01, 0.1, 1, 10} tuned by inner validation. Produce the sensitivity vs false-alarms-per-hour trade-off figure.
- **S7 Fixed point:** integer model of band-pass, DWT, accumulators (widths per plan Section 5), SVM weights; sweep B in {8, 10, 12, 14, 16}; report feature error and event metrics vs B; export hex vectors (input, per-level DWT, features, score) for one seizure and one non-seizure clip.
- **S8 RTL:** (M3/M4 or on request) `dwt_db4.v` single-level analysis pair + decimator and testbench against the vectors; skeletons for SVM MAC, k-in-a-row alarm and UART RX at 230,400 baud. Simulate with Icarus Verilog or Vivado xsim. Label unsimulated code clearly.
- **S9 Report + packaging:** produce `report/midterm.tex` following the outline in plan Section 10 (IEEE CVF template as in the preliminary report), fix all unresolved references, update Table 1, fill the AI-usage statement from the ledger, README, clean-room rerun, zip code.

## 7. Checkpoints (stop and ask the user)

- After S1 subject selection (confirm the eligible cases and the files to download).
- When data is needed but unavailable offline.
- Before changing any frozen protocol parameter.
- If a result looks implausible (for example 100% sensitivity with zero false alarms): investigate leakage and alignment first, report findings, then ask.
- Before S9 final packaging: show the user the results tables and figures for approval.

## 8. Known issues to handle

- The preliminary report PDF shows unresolved references (`[?]`, `Sec. ??`, `Table ??`). Fix `.bib` keys and compile with pdflatex, bibtex, pdflatex, pdflatex; check for zero "?" in the output.
- `context.txt` (if present) has some unverified claims (Wang et al. as FFT, seizure count 182). Use the plan's versions.
- Wang et al. is not the replication target. Shoeb and Guttag is.
- Literature entries marked "Not verified" must stay marked until the user provides the full text.

## 9. Definition of done (all must be true before you say "finished")

- [ ] Subjects, channels, file list frozen and documented
- [ ] Pipeline runs end to end from a clean checkout following README
- [ ] Per-subject sensitivity, false detections per hour, latency for DWT + linear SVM, with the k trade-off
- [ ] Shoeb-style replication with a protocol-difference table and honest verdict
- [ ] Fixed-point model, word-length study, exported hex vectors
- [ ] RTL level-1 DWT verified in simulation, or an explicit statement that it is not done
- [ ] Report draft with zero unresolved references, Table 1 updated, AI-usage and contributions complete
- [ ] All code has header comments; `process.md` is complete and current

## 10. Start now

Begin with **S0**: read `PROJECT_PLAN.pdf`, then create the folder layout, `config.py`, `README.md` and `process.md` (with the template above), set up the environment, and log Entry 1. Then proceed to **S1** and stop at its checkpoint.
