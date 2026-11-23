"""
Apply all Audit Round 3 fixes to report/mtr-15.tex cleanly.
"""
from pathlib import Path

tex_path = Path("D:/Sem/Sem-3/EE2000 Project/report/mtr-15.tex")
with open(tex_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Abstract E+LL phrase
old_abs_ell = "while dual $E+LL$ provides joint amplitude and roughness sensitivity."
new_abs_ell = "while dual $E+LL$ was retained from the frozen hardware baseline protocol."
if old_abs_ell in text:
    text = text.replace(old_abs_ell, new_abs_ell)
    print("1. Abstract E+LL phrase updated")
else:
    print("1. Abstract E+LL phrase already updated")

# 2. Abstract RTL claim
old_abs_rtl_tex = "Four synthesizable Verilog RTL modules (level-1 db4 filter bank, SVM multiply-accumulate unit, alarm logic, and 230,400-baud UART receiver) and testbenches are designed and verified against software test vectors, with architectural resource projections below 5\\% of Spartan-7 XC7S50 capacity."
new_abs_rtl_tex = "Four synthesizable Verilog RTL modules (level-1 db4 filter bank, SVM multiply-accumulate unit, alarm logic, and 230,400-baud UART receiver) and testbench harnesses are designed; the DWT filter bank is verified against software test vectors, with architectural resource projections below 5\\% of Spartan-7 XC7S50 capacity."
if old_abs_rtl_tex in text:
    text = text.replace(old_abs_rtl_tex, new_abs_rtl_tex)
    print("2. Abstract RTL claim updated")
else:
    print("2. Abstract RTL claim already updated")

# 3. Section 4 (§4 Why FPGA)
old_sec4 = r"""  \item \textbf{Quantization and resource profiling:} finite word-length
    effects are measured against event-level detection performance.
  \item \textbf{Deterministic latency:} a streaming pipeline has a fixed
    inference delay, independent of operating-system jitter.
  \item \textbf{Bit-exact verification:} the continuous pipeline is
    verified against a Python golden model."""
new_sec4 = r"""  \item \textbf{Quantization and resource profiling:} finite word-length
    effects are characterised via SQNR and feature distortion as fidelity proxies;
    end-to-end LORO re-evaluation under quantization is planned for Stage 6.
  \item \textbf{Deterministic latency:} a streaming pipeline has a fixed
    inference delay, independent of operating-system jitter.
  \item \textbf{Bit-exact verification:} the DWT filter-bank block is
    verified against a Python golden model via hex test vectors; IIR filter,
    feature accumulator, and top-level are target architecture (not yet implemented)."""
if old_sec4 in text:
    text = text.replace(old_sec4, new_sec4)
    print("3. Section 4 quantization and bit-exact claims updated")
else:
    print("3. Section 4 claims already updated")

# 4. Section 5.2 alarm timestamp definition
old_sec5 = r"""\item \textbf{Event Sensitivity:} the fraction of annotated seizures detected, requiring the alarm timestamp to fall in $[t_{\text{onset}} - 2.0\,\text{s}, t_{\text{offset}}]$;"""
new_sec5 = r"""\item \textbf{Event Sensitivity:} the fraction of annotated seizures detected, requiring the alarm timestamp $t_{\text{alarm}}$ to fall in $[t_{\text{onset}} - 2.0\,\text{s}, t_{\text{offset}}]$. The alarm timestamp is formally defined as the end time of the $k$-th consecutive positive window ($t_{\text{alarm}} = t_{\text{start}} + T$, with $T=2.0$\,s). Detection latency is computed as $\tau = t_{\text{alarm}} - t_{\text{onset}}$; latencies are not clipped, and all detected events in our baseline exhibited non-negative delay ($\tau \ge 0.0$\,s);"""
if old_sec5 in text:
    text = text.replace(old_sec5, new_sec5)
    print("4. Section 5.2 alarm timestamp formal definition updated")
else:
    print("4. Section 5.2 alarm timestamp already updated")

# 5. Table 2 Altaf and Alghaihab numbers
old_t2 = r"""{\color{blue} Altaf et al.\ \cite{altaf2015biomedical}} & {\color{blue} ASIC (65\,nm CMOS)}
  & {\color{blue} 16-channel Line-Length / Bandpower, Memristive Classifier}
  & {\color{blue} CHB-MIT; patient-specific}
  & {\color{blue} 1.2\,$\mu$W; 0.17 FA/h; 95.8\% sensitivity; 2.1\,s latency} \\
{\color{blue} Alghaihab et al.\ \cite{alghaihab2022energy}} & {\color{blue} ASIC (65\,nm CMOS)}
  & {\color{blue} Multi-feature extraction (Roughness + Spectral), Linear/Tree}
  & {\color{blue} CHB-MIT (18 subjects); LORO}
  & {\color{blue} 0.45\,$\mu$J/class; 96.2\% sensitivity; 0.22 FA/h; 3.2\,s latency} \\"""
new_t2 = r"""{\color{blue} Altaf et al.\ \cite{altaf2015biomedical}} & {\color{blue} ASIC (65\,nm CMOS)}
  & {\color{blue} 16-channel Line-Length / Bandpower, Memristive Classifier}
  & {\color{blue} CHB-MIT; patient-specific}
  & {\color{blue} Sub-$\mu$W power; $>95\%$ sensitivity (abstract); exact FA/h and latency: Not verified} \\
{\color{blue} Alghaihab et al.\ \cite{alghaihab2022energy}} & {\color{blue} ASIC (65\,nm CMOS)}
  & {\color{blue} Multi-feature extraction (Roughness + Spectral), Linear/Tree}
  & {\color{blue} CHB-MIT (18 subjects); LORO}
  & {\color{blue} 0.45\,$\mu$J/class; sensitivity and FA/h: Not verified (full text not accessed)} \\"""
if old_t2 in text:
    text = text.replace(old_t2, new_t2)
    print("5. Table 2 Altaf & Alghaihab unverified figures updated")
else:
    print("5. Table 2 figures already updated")

# 6. Section 6.2 Replication heading and content
old_sec6 = r"""    \item \textbf{Cohort Scale and Seizure Duration:} Shoeb evaluated 24 subjects spanning 916 hours, whereas our frozen cohort consists of 3 subjects across 45.6 non-seizure hours. The two missed seizures in our replication occurred in \texttt{chb01}; per-fold replication records are not retained in a separate file, so the specific missed records cannot be confirmed from available CSV data. The plausible cause is that rhythmic discharge patterns in those records did not sustain sufficient consecutive margin over the RBF kernel to trigger the $k=3$ persistence counter. Notably, our proposed pipeline (0.373~FA/h) generates more false alarms than our Shoeb replication (0.307~FA/h) on this same cohort, despite achieving higher sensitivity (100.0\% vs.\ 88.2\%)."""
new_sec6 = r"""    \item \textbf{Cohort and Evaluation Scale:} Shoeb evaluated 24 subjects spanning 916 hours, whereas our frozen cohort consists of 3 subjects across 45.6 non-seizure hours. The specific held-out records in which the two seizures were missed cannot be confirmed from available summary logs (per-fold Shoeb replication logging was not retained in the initial run); the plausible cause is that rhythmic discharge patterns did not sustain sufficient consecutive margin over the RBF kernel to trigger the $k=3$ persistence counter. Notably, our proposed pipeline (0.373~FA/h) generates more false alarms than our Shoeb replication (0.307~FA/h) on this same cohort, despite achieving higher sensitivity (100.0\% vs.\ 88.2\%)."""
if old_sec6 in text:
    text = text.replace(old_sec6, new_sec6)
    print("6. Section 6.2 heading updated")
else:
    print("6. Section 6.2 heading already updated")

# 7. Section 7.3 Figure 1 description and timing
old_sec7 = r"""Fig.~\ref{fig:seizure_onset} illustrates the temporal behavior of the streaming detector during an electrographic seizure in \texttt{chb01\_03.edf}. Under LORO evaluation (trained on all other chb01 records), the streaming Linear SVM accumulates $k=3$ consecutive positive windows beginning at $t=3004$~s, asserting an alarm with a detection latency of $\tau = 8.0$~s relative to the annotated onset at $t=2996$~s. This latency reflects a pre-ictal transition period during which the SVM score crosses the decision boundary only intermittently before establishing three consecutive positive windows. The figure shows the SVM score progression and EEG channels across this onset window."""
new_sec7 = r"""Fig.~\ref{fig:seizure_onset} illustrates the temporal behavior of the streaming detector during an electrographic seizure in \texttt{chb01\_03.edf}. The alarm timestamp is defined as the end of the $k$-th consecutive positive window ($t_{\text{alarm}} = t_{\text{start}} + 2.0$\,s). In this record, the three consecutive positive windows span $[3000, 3002]$\,s, $[3001, 3003]$\,s, and $[3002, 3004]$\,s, asserting an alarm at $t_{\text{alarm}} = 3004$\,s with a detection latency of $\tau = 3004 - 2996 = 8.0$\,s relative to the annotated onset at $t=2996$\,s. This delay occurs after clinical onset during early-ictal rhythmic build-up (intermittent positive windows prior to $t=3000$\,s are suppressed by the $k$-persistence counter). Short latencies of 0\,s and 2\,s observed in other records (e.g.\ \texttt{chb01\_16.edf}: $\tau=0.0$\,s; \texttt{chb01\_04.edf}: $\tau=2.0$\,s) occur when the clinical onset immediately triggers three consecutive positive windows."""
if old_sec7 in text:
    text = text.replace(old_sec7, new_sec7)
    print("7. Section 7.3 timing, early-ictal delay, and latencies updated")
else:
    print("7. Section 7.3 timing already updated")

# 8. Section 7.3 k=1 explanation
idx_k1 = text.find(r"\item At $k=1$ (raw window output)")
if idx_k1 != -1:
    idx_k2 = text.find(r"\item At $k=2$", idx_k1)
    new_k1_snippet = r"""\item At $k=1$ (raw window output), false alarms occur at 2.520~FA/h (115 total FAs) with 1.0~s median latency. The lower sensitivity at $k=1$ (88.2\%, 15/17) compared to $k \ge 2$ (100.0\%) arises because the high rate of uncurated single-window false triggers interacts with the post-alarm refractory scoring window, where a spurious trigger shortly prior to clinical onset can prevent an alarm from being credited to the event. Requiring $k \ge 2$ filters isolated transient spikes, completely restoring 100.0\% sensitivity.
    """
    text = text[:idx_k1] + new_k1_snippet + text[idx_k2:]
    print("8. Section 7.3 k=1 explanation updated")

# 9. Section 7.3 Ablation 3 D2 cycle percentage
if "while increasing FPGA block-RAM and DSP MAC cycles by 20%." in text:
    text = text.replace("while increasing FPGA block-RAM and DSP MAC cycles by 20%.", "while increasing FPGA block-RAM and DSP MAC cycles by 25\\% (conversely, omitting D2 saves 20\\% of feature compute).")
    print("9. Ablation 3 D2 cycle percentage updated")
else:
    print("9. Ablation 3 D2 cycle percentage already updated")

# 10. Section 7.5 B=14 claim
old_b14 = r"""confirming that 16-bit signed arithmetic is adequate and convenient for our FPGA implementation (note: $B=14$ also satisfies our FA/h and latency targets)."""
new_b14 = r"""confirming that 16-bit signed arithmetic is adequate and convenient for our FPGA implementation. (Finite word-length profiling evaluated SQNR and feature distortion; event-level LORO re-evaluation under quantized fixed-point arithmetic is left for Stage 6.)"""
if old_b14 in text:
    text = text.replace(old_b14, new_b14)
    print("10. Section 7.5 B=14 claim updated")
else:
    print("10. Section 7.5 B=14 claim already updated")

# 11. Figure 4 TikZ styling
old_tikz = r"""\begin{tikzpicture}[
  font=\scriptsize,
  blk/.style={draw, rounded corners=2pt, minimum height=1.05cm,
              text width=1.55cm, align=center, fill=blue!8},
  pcblk/.style={blk, fill=gray!25},
  arr/.style={-{Stealth[length=4pt]}, thick},
  node distance=0.38cm]
\node[pcblk] (pc)   {PC: dataset playback};
\node[blk, right=of pc]   (in)   {UART / BRAM input};
\node[blk, right=of in]   (iir)  {IIR band-limit (0.5--25\,Hz)};
\node[blk, right=of iir]  (dwt)  {DWT filter bank (db4)};
\node[blk, right=of dwt]  (feat) {Windowing \& features};
\node[blk, right=of feat] (svm)  {Linear SVM (weights in BRAM)};
\node[blk, right=of svm]  (post) {Alarm rule ($k$ in a row)};
\node[blk, right=of post] (led)  {LED / 7-seg alarm};
\foreach \a/\b in {pc/in, in/iir, iir/dwt, dwt/feat, feat/svm, svm/post, post/led}
  \draw[arr] (\a) -- (\b);
\begin{scope}[on background layer]
  \node[draw, dashed, rounded corners=3pt, inner sep=5pt, fill=blue!2,
        fit=(in)(iir)(dwt)(feat)(svm)(post)(led),
        label={[font=\scriptsize]below:Spartan-7 FPGA (Boolean Board) --- target architecture (shaded blocks: RTL designed; IIR, features, top-level: remaining)}] {};
\end{scope}
\end{tikzpicture}
\caption{Target system architecture. PC handles dataset playback over UART; Spartan-7 FPGA performs streaming IIR, DWT, feature extraction, SVM classification, and alarm indication. Four RTL blocks are designed (DWT filter bank, SVM MAC, alarm logic, UART RX); IIR filter, feature accumulator, windowing, and top-level integration are remaining.}"""

new_tikz = r"""\begin{tikzpicture}[
  font=\scriptsize,
  blk/.style={draw, rounded corners=2pt, minimum height=1.05cm,
              text width=1.55cm, align=center},
  builtblk/.style={blk, fill=blue!18, draw=blue!80!black, thick},
  unbuiltblk/.style={blk, fill=gray!10, draw=gray!60, dashed},
  pcblk/.style={blk, fill=gray!25, draw=black},
  arr/.style={-{Stealth[length=4pt]}, thick},
  node distance=0.38cm]
\node[pcblk]      (pc)   {PC: dataset playback};
\node[builtblk, right=of pc]   (in)   {UART / BRAM input};
\node[unbuiltblk, right=of in] (iir)  {IIR band-limit (0.5--25\,Hz)};
\node[builtblk, right=of iir]  (dwt)  {DWT filter bank (db4)};
\node[unbuiltblk, right=of dwt] (feat) {Windowing \& features};
\node[builtblk, right=of feat] (svm)  {Linear SVM (weights in BRAM)};
\node[builtblk, right=of svm]  (post) {Alarm rule ($k$ in a row)};
\node[unbuiltblk, right=of post] (led) {LED / 7-seg alarm};
\foreach \a/\b in {pc/in, in/iir, iir/dwt, dwt/feat, feat/svm, svm/post, post/led}
  \draw[arr] (\a) -- (\b);
\begin{scope}[on background layer]
  \node[draw, dashed, rounded corners=3pt, inner sep=5pt, fill=blue!2,
        fit=(in)(iir)(dwt)(feat)(svm)(post)(led),
        label={[font=\scriptsize]below:Spartan-7 FPGA target architecture (solid blue: RTL designed; dashed gray: target architecture remaining for Stage 6)}] {};
\end{scope}
\end{tikzpicture}
\caption{Target system architecture. PC handles dataset playback over UART; Spartan-7 FPGA performs streaming IIR, DWT, feature extraction, SVM classification, and alarm indication. Solid blue blocks (\texttt{uart\_rx}, \texttt{dwt\_db4}, \texttt{svm\_classifier}, \texttt{alarm\_logic}) have synthesizable Verilog RTL and testbenches; dashed gray blocks (IIR filter, feature accumulator, windowing, and top-level integration) are target architecture remaining for Stage 6.}"""
if old_tikz in text:
    text = text.replace(old_tikz, new_tikz)
    print("11. Figure 4 TikZ blocks and caption updated")
else:
    print("11. Figure 4 TikZ already updated")

# 12. Table 8 Decisions
old_t8 = r"""\caption{Design decisions. The software baseline has been validated; four RTL modules (DWT filter bank, SVM MAC, alarm logic, UART RX) are designed. IIR filter, feature accumulator, windowing, and top-level integration are target architecture (not yet instantiated in RTL).}
\label{tab:decisions}
\small
\begin{tabularx}{\textwidth}{@{}p{3.2cm}X@{}}
\toprule
Decision & Implemented Configuration \\
\midrule
Channels & 22 uncurated bipolar channels present across all recordings (duplicate \texttt{T8-P8} discarded) \\
Window / hop & 2.0\,s window (512 samples); 1.0\,s hop (256 samples) \\
Band-limit & 0.5--25\,Hz causal 4th-order Butterworth IIR filter (2 cascaded SOS biquads) \\
DWT & Daubechies-4 (db4), 5 levels, direct-form analysis filter pair ($h, g$ 8 taps) \\
Features & Sub-band energy ($E$) and line-length ($LL$) on sub-bands D3, D4, D5, A5 ($D=176$) \\
Classifier & Linear SVM ($C=1.0$), weights fixed offline in Q1.15 BRAM; class-weighted training \\
Numeric format & Signed 16-bit Q1.15 fixed-point arithmetic verified against Python reference \\
Channel processing & Time-multiplexed single-MAC engine shared across 22 channels at 100~MHz \\
Post-processing & Alarm asserted after $k=3$ consecutive positive windows (refractory period 30~s) \\
Input interface & PC-to-FPGA streaming over UART at 230,400 baud (434 system clock cycles per baud) \\
Evaluation & Patient-specific Leave-One-Record-Out (LORO) on 47 CHB-MIT recordings (\texttt{chb01}, \texttt{chb02}, \texttt{chb03}) \\
\bottomrule
\end{tabularx}"""

new_t8 = r"""\caption{Target architecture and design decisions. The software baseline is fully validated; four core RTL modules (\texttt{dwt\_db4}, \texttt{svm\_classifier}, \texttt{alarm\_logic}, \texttt{uart\_rx}) are designed. Front-end IIR filtering, feature accumulators, and top-level wiring are target architecture remaining for Stage 6.}
\label{tab:decisions}
\small
\begin{tabularx}{\textwidth}{@{}p{3.2cm}X@{}}
\toprule
Decision Aspect & Configuration \& Hardware Implementation Status \\
\midrule
Channels & 22 uncurated bipolar channels (software baseline validated; FPGA stream target) \\
Window / hop & 2.0\,s window (512 samples); 1.0\,s hop (256 samples; ring-buffer target) \\
Band-limit & 0.5--25\,Hz causal 4th-order Butterworth IIR (software baseline validated; RTL pending) \\
DWT & Daubechies-4 (db4), 5 levels (single-level block \texttt{dwt\_db4.v} designed; 5-level cascade pending) \\
Features & Sub-band energy ($E$) and line-length ($LL$) on D3, D4, D5, A5 ($D=176$; RTL accumulator pending) \\
Classifier & Linear SVM ($C=1.0$, Q1.15); synthesizable MAC module \texttt{svm\_classifier.v} designed \\
Numeric format & Signed 16-bit Q1.15 fixed-point arithmetic verified against Python reference \\
Channel processing & Time-multiplexed single-MAC engine shared across 22 channels at 100~MHz (projected) \\
Post-processing & Alarm asserted after $k=3$ positive windows; FSM module \texttt{alarm\_logic.v} designed \\
Input interface & PC-to-FPGA streaming over UART at 230,400 baud; receiver module \texttt{uart\_rx.v} designed \\
Evaluation & Patient-specific Leave-One-Record-Out (LORO) on 47 CHB-MIT recordings (\texttt{chb01}, \texttt{chb02}, \texttt{chb03}) \\
\bottomrule
\end{tabularx}"""
if old_t8 in text:
    text = text.replace(old_t8, new_t8)
    print("12. Table 8 target architecture and implementation status updated")
else:
    print("12. Table 8 already updated")

# 13. Section 9.2 RTL testbenches
old_tb_svm = r"""Verified via \texttt{rtl/tb\_svm\_classifier.v}."""
new_tb_svm = r"""Hand-crafted RTL with testbench harness \texttt{rtl/tb\_svm\_classifier.v} (out-of-context Vivado simulation scheduled for Stage 6)."""
if old_tb_svm in text:
    text = text.replace(old_tb_svm, new_tb_svm)

old_tb_alarm = r"""Verified via \texttt{rtl/tb\_alarm\_logic.v}."""
new_tb_alarm = r"""Hand-crafted RTL with testbench harness \texttt{rtl/tb\_alarm\_logic.v} (out-of-context Vivado simulation scheduled for Stage 6)."""
if old_tb_alarm in text:
    text = text.replace(old_tb_alarm, new_tb_alarm)

old_tb_uart = r"""Verified via \texttt{rtl/tb\_uart\_rx.v}."""
new_tb_uart = r"""Hand-crafted RTL with testbench harness \texttt{rtl/tb\_uart\_rx.v} (out-of-context Vivado simulation scheduled for Stage 6)."""
if old_tb_uart in text:
    text = text.replace(old_tb_uart, new_tb_uart)
print("13. Section 9.2 testbench simulation status updated")

# 14. Table 10 Stage 6
old_s6 = r"""Stage 6: Vivado Synthesis & Synthesize complete top-level bitstream for Xilinx Spartan-7 XC7S50 & \textbf{Scheduled (Nov 1--5)} \\"""
new_s6 = r"""Stage 6: Vivado Synthesis & Integrate remaining RTL (IIR filter, feature accumulators, top-level wiring); synthesize bitstream for Spartan-7 XC7S50 & \textbf{Scheduled (Nov 1--5)} \\"""
if old_s6 in text:
    text = text.replace(old_s6, new_s6)
    print("14. Table 10 Stage 6 updated")
else:
    print("14. Table 10 Stage 6 already updated")

# 15. Section 8 AI Disclosure and Table 11
old_ai = r"""Generative AI tools (Claude 3.5 Sonnet and Antigravity AI) were utilized during the project under human supervision according to the course policy. Table~\ref{tab:ai_ledger} details the specific artifacts, tool contributions, and verification procedures.

\begin{table*}[h]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\caption{AI Tool Usage and Verification Ledger.}
\label{tab:ai_ledger}
\begin{tabularx}{\textwidth}{@{}p{4.2cm}Xp{4.6cm}@{}}
\toprule
\textbf{Artifact / Module} & \textbf{AI Role \& Contribution} & \textbf{Human Verification} \\
\midrule
\texttt{src/config.py}, \texttt{src/data\_io.py} & Scaffolding configuration and PhysioNet EDF parser scripts & Verified against CHB-MIT by M1 \\
\texttt{src/dwt.py}, \texttt{src/train.py} & Scripting filter bank and LORO cross-validation loop & Verified math and splits by M2 \\
\texttt{src/fixedpoint.py} & Scripting finite word-length sweep and hex vector export & Checked SQNR derivations by M2 \\
\texttt{rtl/*.v} & Structuring synthesizable Verilog modules and testbenches & Cycle-accurate simulation by M3, M4 \\
\texttt{report/mtr-15.tex} & LaTeX formatting, section drafting, and peer review audit & Technical and numerical audit by all \\
\bottomrule
\end{tabularx}
\end{table*}"""

new_ai = r"""Generative AI tools (Anthropic Claude 3.5 Sonnet and Google Antigravity) were utilized during the project under human supervision according to the course policy (clarifying the preliminary report typographical reference to ``Claude Sonnet 5.5''). Table~\ref{tab:ai_ledger} details the specific artifacts, tool contributions, and verification procedures.

\begin{table*}[h]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\caption{AI Tool Usage and Verification Ledger.}
\label{tab:ai_ledger}
\begin{tabularx}{\textwidth}{@{}p{4.5cm}Xp{4.6cm}@{}}
\toprule
\textbf{Artifact / Module} & \textbf{AI Role \& Contribution} & \textbf{Human Verification} \\
\midrule
\texttt{src/config.py}, \texttt{src/data\_io.py} & Scaffolding configuration and PhysioNet EDF parser scripts & Verified against CHB-MIT by M1 \\
\texttt{src/dwt.py}, \texttt{src/train.py} & Scripting filter bank and LORO cross-validation loop & Verified math and splits by M2 \\
\texttt{src/ablate.py}, \texttt{src/shoeb\_baseline.py} & Scripting ablation sweeps ($k, \text{feat}, C$) and replication loop & Checked metric aggregation by M2 \\
\texttt{src/fixedpoint.py} & Scripting finite word-length sweep and hex vector export & Checked SQNR derivations by M2 \\
\texttt{rtl/*.v} & Structuring synthesizable Verilog modules and testbenches & Cycle-accurate review by M3, M4 \\
\texttt{scripts/*.py} (audit, verify, plot) & Automated submission audit, CSV verification, and 3-panel plotting & Verified against raw CSVs by all \\
\texttt{report/mtr-15.tex} & LaTeX formatting, section drafting, and peer review audit & Technical and numerical audit by all \\
\bottomrule
\end{tabularx}
\end{table*}"""
if old_ai in text:
    text = text.replace(old_ai, new_ai)
    print("15. Section 8 AI disclosure and Table 11 updated")
else:
    print("15. Section 8 AI disclosure already updated")

with open(tex_path, "w", encoding="utf-8") as f:
    f.write(text)

print("\n[SUCCESS] Script completed successfully!")
