# Technical Repository Analysis: Existing Implementation & FPGA Compatibility

**Project:** FPGA-Based Multichannel EEG Seizure Detection System  
**Target Hardware:** RealDigital Boolean Board (AMD/Xilinx Spartan-7 XC7S50, `xc7s50csga324-1`, 100 MHz System Clock)  
**Document Purpose:** Baseline technical audit and architectural reconstruction of existing software, models, and hardware interfaces prior to experiment framework implementation.

---

## 1. Repository Inventory and Git State

### Current Working Tree State
- **Git Branch:** `main` (initial uncommitted working tree baseline; pending staging).
- **Core Directories:**
  - `src/`: Python software pipeline for dataset ingestion, preprocessing, DWT feature extraction, model training, evaluation, and fixed-point exploratory sweeps.
  - `rtl/`: Synthesizable Verilog-2001 RTL modules and self-checking testbenches targeting the Spartan-7 XC7S50 FPGA.
  - `golden/`: Bit-accurate dual-mode (Float64 and Integer Fixed-Point) golden software model and hex test vectors.
  - `data/`: Dataset metadata, summary parsing logs (`chb01-summary.txt`, `chb02-summary.txt`, `chb03-summary.txt`), and `manifest.csv` specifying the 47 frozen recordings.
  - `tools/`: FPGA model export utilities (`export_svm.py`).
  - `scripts/`: Hardware demonstration harnesses (`stream_eeg_uart.py`), Vivado synthesis TCL scripts (`run_vivado_synth.tcl`), and historical fixed-point comparison runners (`run_fixedpoint_loro.py`).
  - `results/`: Historical benchmark logs, fold CSVs, model pickle checkpoints (`results/models/`), and playback logs.
  - `fpr-15/`: Identical mirror copy of `rtl/`, `src/`, and `vectors/` retained from previous project archive.
  - `audit/`: Complete Phase 1 technical audit documentation.

---

## 2. Dataset Ingestion and Channel Selection Protocol

### Dataset Specification
- **Database:** CHB-MIT Scalp EEG Database (PhysioNet).
- **Sampling Frequency ($f_s$):** $256\text{ Hz}$.
- **Selected Cohort:** Patients `chb01`, `chb02`, and `chb03`.
  - Criteria evaluated in [src/data_io.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/data_io.py#L102-L171):
    1. Case must have $\ge 3$ annotated clinical seizures.
    2. Case must have a consistent 23-channel bipolar montage with no non-EEG channels (e.g., ECG or VNS).
    3. `chb21` excluded (same patient as `chb01`).
- **Manifest Breakdown ([data/manifest.csv](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/data/manifest.csv)):**
  - Total records selected: **47 recordings**.
  - Seizure-containing records: **11 recordings** (7 in `chb01`, 3 in `chb02`, 1 in `chb03`), containing a total of **17 clinical seizures**.
  - Seizure-free background records: **36 recordings** (nominally ~1 hour each) providing **$45.63\text{ hours}$** of interictal baseline for false-alarm rate estimation.

### Channel Montage Deduplication
The standard CHB-MIT recording montage contains 23 raw signal labels. However, entries 15 and 23 are both labelled `T8-P8` (duplicate recording lead).
In [src/config.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/config.py#L38-L60) and [src/data_io.py](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/data_io.py#L240-L246), the duplicate channel is mapped to its first occurrence, establishing a canonical **22 unique bipolar channels**:
```python
CHANNELS_22 = [
    "FP1-F7", "F7-T7", "T7-P7", "P7-O1",
    "FP1-F3", "F3-C3", "C3-P3", "P3-O1",
    "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
    "FP2-F8", "F8-T8", "T8-P8", "P8-O2",
    "FZ-CZ",  "CZ-PZ", "P7-T7", "T7-FT9",
    "FT9-FT10", "FT10-T8"
]
```
The FPGA ingestion logic and software pipelines strictly process channels in this 22-channel order ($0\le \text{channel\_id} \le 21$).

---

## 3. Signal Processing and Feature Extraction

### Preprocessing and Digital Filtering
1. **Causal Bandpass Filter:**
   - Causal 4th-order Butterworth bandpass filter spanning $0.5\text{ Hz}$ to $25.0\text{ Hz}$ implemented as two cascaded Second-Order Sections (SOS / biquads) at $f_s = 256\text{ Hz}$.
   - Software: `scipy.signal.sosfilt` with forward-only causal processing ([src/dwt.py#L42-L49](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/dwt.py#L42-L49)).
   - Hardware: Time-multiplexed 22-channel Direct Form I biquad cascade running in fixed-point with Q20 internal coefficient scaling ([rtl/iir_biquad.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/iir_biquad.v)).
   - State reset: Filter state is maintained continuously across samples within each recording, but reset between independent recordings to prevent cross-record leakage.

### Wavelet Decomposition (db4 DWT)
- **Wavelet Type:** Daubechies-4 (db4), 8-tap finite impulse response filters.
- **Decomposition Depth:** 5 levels ($J=5$).
- **Frequency Subbands:**
  - $D_1$: $64 - 128\text{ Hz}$ (discarded, high-frequency noise).
  - $D_2$: $32 - 64\text{ Hz}$ (discarded in baseline; line-noise band).
  - $D_3$: $16 - 32\text{ Hz}$ (**retained**; Beta band).
  - $D_4$: $8 - 16\text{ Hz}$ (**retained**; Alpha band).
  - $D_5$: $4 - 8\text{ Hz}$ (**retained**; Theta band).
  - $A_5$: $0 - 4\text{ Hz}$ (**retained**; Delta band).
- **Subbands Retained:** 4 subbands ($D_3, D_4, D_5, A_5$).

### Feature Definitions
For each retained subband $b \in \{D_3, D_4, D_5, A_5\}$ containing $N_b$ wavelet coefficients $c_b[n]$:
1. **Subband Energy ($E_b$):**
   $$E_b = \frac{1}{N_b} \sum_{n=0}^{N_b-1} c_b[n]^2$$
2. **Subband Line-Length ($LL_b$):**
   $$LL_b = \frac{1}{N_b - 1} \sum_{n=1}^{N_b-1} |c_b[n] - c_b[n-1]|$$

### Feature Vector Geometry
- Channels: 22
- Subbands: 4 ($D_3, D_4, D_5, A_5$)
- Features per subband: 2 ($E_b$, then $LL_b$)
- **Total Feature Dimension:** $22 \times 4 \times 2 = \mathbf{176\text{ features}}$.
- **Feature Ordering:** Serialized channel-major, subband-major, feature-type minor:
  - Feature 0: Ch 0, D3 Energy
  - Feature 1: Ch 0, D3 Line-Length
  - Feature 2: Ch 0, D4 Energy
  - Feature 3: Ch 0, D4 Line-Length
  - ...
  - Feature 174: Ch 21, A5 Energy
  - Feature 175: Ch 21, A5 Line-Length

---

## 4. Problem A: Training and FPGA Window Mismatch

### Software Baseline Configuration
In the existing software machine learning pipeline ([src/config.py#L62-L65](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/config.py#L62-L65), [src/train.py#L50-L95](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/train.py#L50-L95)):
- **Window Length:** $2.0\text{ seconds}$ ($W = 512\text{ samples}$ at $256\text{ Hz}$).
- **Hop Length:** $1.0\text{ second}$ ($H = 256\text{ samples}$, $50\%$ overlap).
- **Wavelet Coefficient Counts ($N_b$) per 2.0s window:**
  $$N_{\text{D3}} = 64, \quad N_{\text{D4}} = 32, \quad N_{\text{D5}} = 16, \quad N_{\text{A5}} = 16$$
- **Window Labeling Rule:** A window is labelled positive ($y=1$) if $\ge 50\%$ of the window duration lies inside an annotated seizure interval ([src/preprocess.py#L32-L64](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/src/preprocess.py#L32-L64)).

### Hardware FPGA Configuration
In the RTL implementation ([rtl/top_seizure_detector.v#L104-L125](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/top_seizure_detector.v#L104-L125), [rtl/feature_accumulator.v#L120-L170](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/feature_accumulator.v#L120-L170)) and golden model ([golden/golden.py#L44-L60](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/golden/golden.py#L44-L60)):
- **Window Length:** $1.0\text{ second}$ ($W = 256\text{ samples}$ at $256\text{ Hz}$).
- **Hop Length:** $1.0\text{ second}$ ($H = 256\text{ samples}$, **non-overlapping**).
- **Wavelet Coefficient Counts ($N_b$) per 1.0s window:**
  $$N_{\text{D3}} = 32, \quad N_{\text{D4}} = 16, \quad N_{\text{D5}} = 8, \quad N_{\text{A5}} = 8$$

### Hardware Normalization Shifting
Inside [rtl/feature_accumulator.v#L135-L165](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/feature_accumulator.v#L135-L165), feature normalization is implemented via bit-shifts:
- **Energy Right-Shifts:**
  - $D_3$ ($N=32$): `>> 20` (accounting for Q15 squaring $2^{30} \to 2^{15}$ shift of 15, plus $\frac{1}{32} = 2^{-5}$ shift of 5 $\implies 15 + 5 = 20$).
  - $D_4$ ($N=16$): `>> 19` ($15 + 4 = 19$).
  - $D_5$ ($N=8$): `>> 18` ($15 + 3 = 18$).
  - $A_5$ ($N=8$): `>> 18` ($15 + 3 = 18$).
- **Line-Length Right-Shifts:**
  - $D_3$ ($N-1=31 \approx 32$): `>> 5`.
  - $D_4$ ($N-1=15 \approx 16$): `>> 4`.
  - $D_5$ ($N-1=7 \approx 8$): `>> 3`.
  - $A_5$ ($N-1=7 \approx 8$): `>> 3`.

### Why Simple Weight Rescaling Does Not Establish Equivalence
In [tools/export_svm.py#L78-L82](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/tools/export_svm.py#L78-L82), the script folded scaling factors assuming $N_b = \{32, 16, 8, 8\}$. While this numerically compensates for the sum length, **the temporal statistics of 1.0-second EEG features differ fundamentally from 2.0-second features**:
1. Line-length and energy computed over 1.0s have significantly higher sample-to-sample variance and kurtosis than features averaged over 2.0s.
2. The empirical mean ($\mu_j$) and standard deviation ($\sigma_j$) computed across the dataset by `StandardScaler` shift.
3. The optimal hyperplane separation margin, class balance weights, and support vectors change.
Deploying weights trained on 2.0s windows onto 1.0s hardware introduces an unquantified distributional shift that directly impacts sensitivity, false-alarm rates, and latency.

---

## 5. Problem B: Fixed-Point Evaluation Authenticity

### The Defect in Existing Verification
In [scripts/run_fixedpoint_loro.py#L57-L66](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/scripts/run_fixedpoint_loro.py#L57-L66):
```python
# 16-bit Q1.15 RTL Fixed-Point Evaluation
# Since SQNR at B=16 is 82.6 dB (sub-microvolt error, 0.003% feature distortion),
# finite word-length noise is 2 orders of magnitude below the SVM decision margin.
# Event-level detection concordance is exactly 100%.
detected_fixed = detected_float
fa_fixed = fa_float
all_latencies_fixed = list(all_latencies_float)
```
The fixed-point cross-validation metrics were **not** generated by running the 47 patient recordings through a bit-exact fixed-point simulator. Instead, the script copied floating-point metrics directly into the fixed-point columns and asserted $100\%$ concordance based purely on an isolated 1-second SQNR test.

### Required Architecture for Genuine Fixed-Point Evaluation
To satisfy research-grade reproducibility and hardware fidelity:
1. Every held-out evaluation window must pass through actual integer fixed-point transformations mirroring RTL bit widths, rounding, and saturation.
2. The integer fixed-point dot product and bias accumulation must be computed in 40-bit signed arithmetic matching [rtl/svm_classifier.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/svm_classifier.v).
3. The alarm logic persistence ($k=3$) and 30-second refractory timer must operate on the integer decision sequence.
4. An automated assertion must check and fail if fixed-point output arrays are accidentally shallow-copied or identical references to floating-point outputs.

---

## 6. Machine Learning Model Training and Cross-Validation

### Training Protocol
- **Classifier:** Linear Support Vector Machine (`LinearSVC`).
- **Hyperparameters:**
  - Penalty parameter $C = 1.0$.
  - Loss: Squared hinge loss.
  - Class weights: `class_weight='balanced'` (critically compensates for severe class imbalance, where interictal background represents $>98\%$ of recording duration).
  - Max iterations: $20,000$.
- **Standardization (Zero-Leakage):**
  - Features are standardized to zero mean and unit variance: $x_{\text{scaled}} = \frac{x - \mu}{\sigma}$.
  - `StandardScaler` is fitted **exclusively on the training fold**.
  - Held-out evaluation records are transformed using the training fold's fitted $\mu$ and $\sigma$.

### Leave-One-Record-Out (LORO) Cross-Validation
For patient $P$ having $M$ eligible recording files:
- For $m = 1, \dots, M$:
  1. Hold out record $m$ as the test record.
  2. Aggregate all windows from the remaining $M - 1$ records of patient $P$ as the training set.
  3. Fit scaler on the training set; transform test record $m$.
  4. Train Linear SVM on the training set.
  5. Evaluate window predictions on test record $m$.
  6. Apply temporal alarm post-processing to obtain event detections, false alarms, and latencies.

### Anti-Leakage Invariants
- **No Random Splitting:** Overlapping or sequential EEG windows from the same recording are never randomly partitioned between train and test.
- **Recording Boundary Isolation:** Windows never cross recording boundaries.
- **Strict Grouping:** Cross-validation is partitioned strictly at the whole-record boundary.

---

## 7. Model Export and RTL Interface Specifications

### Dynamic Scale Folding
The trained software decision function evaluates:
$$\text{Score}_{\text{float}} = \text{intercept} + \sum_{j=0}^{175} \text{coef}_j \cdot \left(\frac{x_j - \mu_j}{\sigma_j}\right)$$
Expanding into effective weights ($w_{\text{eff}, j}$) and effective bias ($b_{\text{eff}}$):
$$w_{\text{eff}, j} = \frac{\text{coef}_j}{\sigma_j}, \quad b_{\text{eff}} = \text{intercept} - \sum_{j=0}^{175} \frac{\text{coef}_j \cdot \mu_j}{\sigma_j}$$
$$\text{Score}_{\text{float}} = b_{\text{eff}} + \sum_{j=0}^{175} w_{\text{eff}, j} \cdot x_j$$

In hardware, feature $x_j$ is represented as an unsigned integer $x_{\text{hw}, j}$ produced by [rtl/feature_accumulator.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/feature_accumulator.v) using ADC input scaling $S_{\text{sig}} = 20\text{ LSB}/\mu\text{V}$ and bit-shifts:
$$x_j \approx x_{\text{hw}, j} \cdot K_j$$
where:
$$K_{E, b} = \frac{2^{\text{shift}_E}}{S_{\text{sig}}^2 \cdot N_b}, \quad K_{LL, b} = \frac{2^{\text{shift}_{LL}}}{S_{\text{sig}} \cdot (N_b - 1)}$$
Substituting:
$$\text{Score} = b_{\text{eff}} + \sum_{j=0}^{175} (w_{\text{eff}, j} \cdot K_j) \cdot x_{\text{hw}, j} = b_{\text{eff}} + \sum_{j=0}^{175} w_{\text{hw}, j} \cdot x_{\text{hw}, j}$$

To map $w_{\text{hw}, j}$ into signed 16-bit integers ($[-32768, 32767]$) without overflow:
$$S_M = \left\lfloor \frac{32767}{\max_j |w_{\text{hw}, j}| \times 1.05} \right\rfloor$$
$$w_{\text{fixed}, j} = \text{round}(w_{\text{hw}, j} \cdot S_M) \in [-32768, 32767]$$
$$b_{\text{fixed}} = \text{round}(b_{\text{eff}} \cdot S_M) \in [-2^{31}, 2^{31}-1]$$
$$\text{Score}_{\text{fixed}} = b_{\text{fixed}} + \sum_{j=0}^{175} w_{\text{fixed}, j} \cdot x_{\text{hw}, j} \approx S_M \cdot \text{Score}_{\text{float}}$$
Because $S_M > 0$, the decision boundary is identical: $\text{sign}(\text{Score}_{\text{fixed}}) = \text{sign}(\text{Score}_{\text{float}})$.

### Hardware Memory Encoding Specifications
- `weights.mem`:
  - Exactly 176 entries (one entry per line).
  - 16-bit signed two's complement in 4-digit hexadecimal format (`%04X`).
  - Read by `svm_classifier.v` via `$readmemh("weights.mem", weight_rom)`.
- `bias.mem`:
  - Exactly 1 entry.
  - 32-bit signed two's complement in 8-digit hexadecimal format (`%08X`).
  - Read via `$readmemh("bias.mem", bias_rom)`.

### Hardware Timing and Interfacing Requirements
- **Classifier Clock Cycles:** [rtl/svm_classifier.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/svm_classifier.v) takes exactly 176 clock cycles ($1.76\ \mu\text{s}$ at 100 MHz) from `start` assertion to `done` pulse.
- **Feature Serial Stream:** Paced at 1 feature per clock cycle over 176 cycles directly from the feature accumulator readout state machine.
- **Temporal Post-Processing:** [rtl/alarm_logic.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/alarm_logic.v) latches an alarm when $k$ consecutive window scores $>0$, and enforces a 30-second refractory blanking window.

---

## 8. Summary of Engineering Goals for Framework Implementation

To establish a professional, publication-grade research and FPGA compatibility framework:
1. **Unified Configuration Schemas:** Define explicit, isolated configurations for Configuration A ($1.0\text{ s}$ non-overlapping, FPGA-native) and Configuration B ($2.0\text{ s}$ $50\%$ overlap, software baseline).
2. **Reproducible Experiment Runner:** Build clean, non-leaking LORO training and evaluation pipelines with automated fold tracking and metrics logging.
3. **Genuine Fixed-Point Simulation:** Implement an end-to-end bit-accurate fixed-point pipeline that validates quantized execution on all held-out records.
4. **FPGA Model Exporter:** Build safe candidate export utilities that output validated `.mem` files, feature ordering maps, and hex test vectors without overwriting active hardware files.
5. **Self-Checking Unit Tests:** Provide regression test suites verifying windowing, feature dimensions, fixed-point arithmetic, and export formatting.
6. **Self-Contained Collaborator Prompts:** Write modular, exhaustive prompts for another engineer to execute the training, evaluation, fixed-point validation, and artifact packaging.
