# COLLABORATOR EXECUTION PROMPT 00: ENVIRONMENT PREFLIGHT & METHODOLOGY VERIFICATION

**Instruction for Collaborator:** Copy and paste this prompt in its entirety into your Antigravity AI assistant to begin the experiment workflow.

---

```markdown
# TASK: ENVIRONMENT PREFLIGHT, DATASET AUDIT, AND METHODOLOGY VERIFICATION

## 0. YOUR ROLE
You are acting as a Senior Machine Learning Systems Engineer and Biomedical DSP Engineer.
You have been provided with an engineered experiment infrastructure in `experiments/window_alignment/` designed to retrain, evaluate, and export an FPGA-compatible EEG seizure detection model on the CHB-MIT Scalp EEG database.

Your immediate objective is to perform comprehensive environment preflight checks, verify all Python dependencies, validate the dataset manifest and raw EDF/NPZ files, and certify that the experiment infrastructure passes all self-checking tests BEFORE any training begins.

Do NOT begin model training in this step. Complete the preflight audit first.

---

## 1. PROJECT CONTEXT & SCIENTIFIC BACKGROUND

- **Project:** 22-Channel FPGA-Based Real-Time EEG Seizure Detection System.
- **Target Hardware:** RealDigital Boolean Board (AMD/Xilinx Spartan-7 XC7S50, `xc7s50csga324-1`, 100 MHz clock).
- **Dataset:** CHB-MIT Scalp EEG Database (PhysioNet).
  - Selected Cohort: Cases `chb01`, `chb02`, and `chb03`.
  - Manifest: 47 total recordings (`data/manifest.csv`) providing 11 seizure recordings (17 clinical seizures) and 36 interictal baseline recordings (~45.63 hours).
- **Core Signal Pipeline:**
  1. 22 unique bipolar EEG channels at $f_s = 256\text{ Hz}$.
  2. Causal 4th-order Butterworth bandpass filter ($0.5 - 25.0\text{ Hz}$).
  3. 5-level Daubechies-4 (db4) Discrete Wavelet Transform (retaining subbands D3, D4, D5, A5).
  4. Feature extraction: Subband Energy and Line-Length ($22\times 4\times 2 = 176\text{ features}$).
  5. Linear Support Vector Machine (Linear SVM) classification.
  6. Temporal alarm post-processing: $k=3$ consecutive window persistence with 30-second refractory blanking.

### The Two Critical Problems You Are Solving:
1. **Problem A (Temporal Window Mismatch):**
   - The historical software baseline (`src/config.py`) used **2.0-second overlapping windows with 1.0-second hop** (512 samples/window; subband coefficient counts $N = \{64, 32, 16, 16\}$).
   - The Spartan-7 FPGA hardware (`rtl/feature_accumulator.v`, `rtl/top_seizure_detector.v`) natively executes on **1.0-second non-overlapping windows** (256 samples/window; subband coefficient counts $N = \{32, 16, 8, 8\}$).
   - You will evaluate both configurations side-by-side to determine if training directly on 1.0s windows establishes genuine hardware compatibility without sacrificing clinical sensitivity.
2. **Problem B (Fixed-Point Evaluation Authenticity):**
   - Previous scripts copied floating-point metrics into fixed-point result tables.
   - You will run a genuine, bit-accurate integer fixed-point evaluation mirroring the 40-bit accumulator RTL arithmetic.

---

## 2. PREFLIGHT STEP-BY-STEP INSTRUCTIONS

### Step 1: Inspect the Experiment Infrastructure
Inspect the following files in the repository:
1. `experiments/window_alignment/configs/window_1s.yaml` (Configuration A: 1.0s FPGA-aligned)
2. `experiments/window_alignment/configs/window_2s.yaml` (Configuration B: 2.0s Software baseline)
3. `experiments/window_alignment/code/config_loader.py`
4. `experiments/window_alignment/code/feature_pipeline.py`
5. `experiments/window_alignment/code/metrics.py`
6. `experiments/window_alignment/code/evaluation.py`
7. `experiments/window_alignment/code/experiment_runner.py`
8. `experiments/window_alignment/code/fixedpoint_evaluation.py`
9. `experiments/window_alignment/code/model_export.py`
10. `experiments/window_alignment/code/validation.py`
11. `experiments/window_alignment/repository_analysis.md`

### Step 2: Verify Python Environment and Dependencies
Run a shell check to verify required libraries:
```bash
python3 -c "
pkgs = ['numpy', 'scipy', 'sklearn', 'pyedflib', 'yaml']
for p in pkgs:
    try:
        __import__(p)
        print(f'[OK] {p}: available')
    except ImportError:
        print(f'[MISSING] {p}: NOT installed')
"
```
If `sklearn`, `pyedflib`, or `yaml` are missing, install them:
```bash
pip install scikit-learn pyedflib pyyaml
```
*(Note: The experiment framework contains built-in zero-dependency fallbacks for `yaml` and `sklearn`, but installing them is recommended for standard scikit-learn LinearSVC training).*

### Step 3: Run the Infrastructure Regression Test Suite
Execute the self-checking unit test suite:
```bash
python3 experiments/window_alignment/tests/run_tests.py
```
**Acceptance Criterion:** All 15 tests must pass with `100% GREEN`:
- `test_windowing`: 1.0s non-overlapping and 2.0s overlapping slicing, label alignment, and short recording handling.
- `test_features`: Dyadic DWT subband lengths, Energy and Line-Length math, 176 feature dimensions.
- `test_loro_split`: Zero-leakage LORO partitioning and train-only standardization.
- `test_fixedpoint`: Hardware scale derivation, 40-bit serial MAC arithmetic, anti-duplication assertions, and bit-exact integer pipeline emulation.
- `test_model_export`: .mem formatting, $readmemh compliance, and bit-exact vector simulation.
- `test_rtl_cosim`: Icarus Verilog co-simulation compiling and executing `rtl/svm_classifier.v` across 9 deterministic edge cases.

### Step 4: Verify CHB-MIT Dataset Availability
1. Check the frozen dataset manifest:
   ```bash
   head -n 25 data/manifest.csv
   wc -l data/manifest.csv
   ```
   Confirm that 47 recordings are listed across `chb01`, `chb02`, and `chb03`.
2. Check if raw EDF files or preprocessed `.npz` files exist:
   ```bash
   ls -la data/raw/
   ls -la data/processed/
   ```
3. If `data/processed/` is empty and raw `.edf` files need to be processed or downloaded from PhysioNet, execute the data preparation pipeline:
   - Check if raw EDF files exist in `data/raw/chb01/`, `data/raw/chb02/`, `data/raw/chb03/`.
   - If downloading is required from PhysioNet (`https://physionet.org/files/chbmit/1.0.0/`), run `src/data_io.py` or download the 47 files specified in `data/manifest.csv`.
   - Run preprocessing:
     ```bash
     python3 src/preprocess.py
     ```
   - Verify that `data/processed/` contains 47 `.npz` files:
     ```bash
     ls data/processed/*.npz | wc -l
     ```

---

## 3. STRICT CONSTRAINTS & SAFETY RULES

- Do NOT overwrite existing files in `rtl/weights.mem` or `rtl/bias.mem`.
- Do NOT overwrite baseline models in `results/models/` or baseline logs in `results/`.
- Do NOT modify the active Verilog RTL during this software phase.
- Do NOT begin model training until all 15 unit tests pass and data availability is certified.

---

## 4. PREFLIGHT REPORT DELIVERABLE

Output a clear preflight summary report answering:
1. **Infrastructure Test Status:** Confirm whether `run_tests.py` passed with 15/15 tests green.
2. **Environment Dependencies:** Status of `numpy`, `scipy`, `scikit-learn`, `pyedflib`, and `pyyaml`.
3. **Dataset Verification:** Exact count of recordings available in `data/processed/` or `data/raw/`.
4. **Configuration Certification:** Confirm that `window_1s.yaml` and `window_2s.yaml` are loaded and understood.
5. **Readiness Statement:** Explicit confirmation: `READY TO PROCEED TO PROMPT_01_TRAIN_AND_EVALUATE`.
```
