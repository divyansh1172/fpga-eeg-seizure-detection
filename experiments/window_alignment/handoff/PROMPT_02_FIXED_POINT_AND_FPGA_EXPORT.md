# COLLABORATOR EXECUTION PROMPT 02: GENUINE FIXED-POINT EVALUATION & FPGA EXPORT

**Instruction for Collaborator:** Copy and paste this prompt in its entirety into your Antigravity AI assistant after completing `PROMPT_01_TRAIN_AND_EVALUATE.md`.

---

```markdown
# TASK: GENUINE BIT-ACCURATE FIXED-POINT EVALUATION AND FPGA CANDIDATE MODEL EXPORT

## 0. YOUR ROLE
You are acting as an FPGA Systems Engineer, Digital Signal Processing Architect, and Hardware-Software Co-Design Specialist.

Your objectives in this phase are:
1. **Execute Genuine Fixed-Point Evaluation:** Run an authentic bit-accurate integer fixed-point evaluation across all held-out evaluation recordings for the 1.0-second FPGA-aligned model (Configuration A).
2. **Quantization Fidelity & Concordance Analysis:** Compare floating-point vs. fixed-point decision scores, evaluate Signal-to-Quantization-Noise Ratio (SQNR), decision agreement percentage, and event-level metrics.
3. **Export Validated FPGA Candidate Model Artifacts:** Use the dedicated exporter to generate `$readmemh`-compatible `.mem` files, feature ordering maps, and test vectors.
4. **Independent Hardware Validation:** Execute `validation.py` to verify bit-exact RTL MAC score reproduction.

---

## 1. HARDWARE ARITHMETIC CONSTRAINTS & THE ANTI-DUPLICATION RULE

### Spartan-7 RTL Hardware Arithmetic
The RTL implementation ([rtl/svm_classifier.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/svm_classifier.v)) computes:
$$\text{Score} = b_{\text{ext}} + \sum_{j=0}^{175} \left(w_{\text{fixed}, j} \times x_{\text{hw}, j}\right)$$
- Features ($x_{\text{hw}, j}$): 16-bit unsigned integers $[0, 32767]$ from [rtl/feature_accumulator.v](file:///Users/divy/Desktop/Github/fpga-eeg-seizure-detection/rtl/feature_accumulator.v).
- Weights ($w_{\text{fixed}, j}$): 16-bit signed two's complement integers $[-32768, 32767]$.
- Multiplier: $16\text{-bit} \times 16\text{-bit} \to 32\text{-bit}$ signed product.
- Accumulator: 40-bit signed accumulator initialized with 32-bit sign-extended bias $b_{\text{fixed}}$.
- Decision: $\text{Decision} = (\text{Score} > 0) \ ?\ 1\ :\ 0$.

### The Anti-Duplication Rule (Addressing Problem B)
In the previous audit, scripts copied floating-point metrics into fixed-point result tables.
**This behavior is strictly prohibited.**
The evaluation engine in `experiments/window_alignment/code/fixedpoint_evaluation.py` enforces automated runtime assertions:
```python
if scores_fixed is scores_float or id(scores_fixed) == id(scores_float):
    raise RuntimeError("CRITICAL ERROR: Fixed-point scores array is identical reference to float array!")
if np.array_equal(scores_fixed, scores_float):
    raise RuntimeError("CRITICAL ERROR: Fixed-point integer scores are identical to float scores!")
```
Your fixed-point results must originate from genuine integer quantization and serial MAC simulation.

---

## 2. STEP-BY-STEP EXECUTION INSTRUCTIONS

### Step 1: Execute Full Fixed-Point Evaluation on Configuration A
Run the fixed-point evaluation script across all subjects:
```bash
python3 -c "
import pickle
import json
from pathlib import Path
import numpy as np
from experiments.window_alignment.code.config_loader import load_config
from experiments.window_alignment.code.experiment_runner import ExperimentRunner
from experiments.window_alignment.code.fixedpoint_evaluation import FixedPointEvaluator

config = load_config('1s')
runner = ExperimentRunner(config_path_or_name='1s')
subjects = config['evaluation']['subjects']

print('=' * 80)
print(' RUNNING GENUINE BIT-ACCURATE FIXED-POINT RTL EVALUATION (CONFIG A: 1.0s)')
print('=' * 80)

all_comparisons = []

for sub in subjects:
    records = runner.load_or_process_subject_records(sub)
    if len(records) < 2:
        continue
        
    for test_idx, test_rec in enumerate(records):
        test_fname = test_rec['filename']
        # Load trained fold model
        model_path = runner.models_dir / f\"{sub}_{Path(test_fname).stem}_model.pkl\"
        if not model_path.exists():
            continue
            
        with open(model_path, 'rb') as f:
            m_data = pickle.load(f)
            
        evaluator = FixedPointEvaluator(config, m_data['clf'], m_data['scaler'])
        
        res = evaluator.evaluate_recording(
            features_float=test_rec['features'],
            window_starts_sec=test_rec['window_starts_sec'],
            seizure_intervals=test_rec['seizure_intervals'],
            duration_sec=test_rec['duration_sec'],
            y_true=test_rec['window_labels']
        )
        
        q_fid = res['quantization_fidelity']
        fl_res = res['float_results']
        fx_res = res['fixed_results']
        
        row = {
            'subject': sub,
            'held_out_record': test_fname,
            'S_M_multiplier': q_fid['S_M_multiplier'],
            'mean_abs_error': q_fid['mean_absolute_score_error'],
            'max_abs_error': q_fid['max_absolute_score_error'],
            'decision_sqnr_db': q_fid['decision_score_sqnr_db'],
            'decision_agreement_pct': q_fid['decision_agreement_percent'],
            'float_detected_sz': fl_res['detected_seizures'],
            'fixed_detected_sz': fx_res['detected_seizures'],
            'total_seizures': fl_res['total_seizures'],
            'float_false_alarms': fl_res['false_alarms'],
            'fixed_false_alarms': fx_res['false_alarms'],
            'non_seizure_hours': fl_res['non_seizure_hours']
        }
        all_comparisons.append(row)
        print(f\"  [{sub} | {test_fname[:16]:16s}] Agreement: {q_fid['decision_agreement_percent']:6.2f}% | \"
              f\"SQNR: {q_fid['decision_sqnr_db']:5.1f} dB | \"
              f\"Sz: Float={fl_res['detected_seizures']}/Fixed={fx_res['detected_seizures']} | \"
              f\"FA: Float={fl_res['false_alarms']}/Fixed={fx_res['false_alarms']}\")

# Export CSV comparison
out_csv = Path('experiments/window_alignment/reports/window_1s_fpga_aligned/fixedpoint_comparison.csv')
out_csv.parent.mkdir(parents=True, exist_ok=True)
if all_comparisons:
    import csv
    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(all_comparisons[0].keys()))
        writer.writeheader()
        writer.writerows(all_comparisons)
    print(f'\n[SAVED] Saved genuine fixed-point comparison report -> {out_csv}')
"
```

### Step 2: Export FPGA Candidate Deployment Models
Export candidate models for subjects `chb01`, `chb02`, and `chb03` using `model_export.py`:
```bash
python3 -c "
from pathlib import Path
from experiments.window_alignment.code.config_loader import load_config
from experiments.window_alignment.code.model_export import export_candidate_model

config = load_config('1s')
models_dir = Path('experiments/window_alignment/artifacts/window_1s_fpga_aligned/models')

for sub in ['chb01', 'chb02', 'chb03']:
    deploy_model = models_dir / f'{sub}_deployment_candidate.pkl'
    if deploy_model.exists():
        print(f'\n[EXPORT] Exporting candidate deployment artifact for {sub}...')
        export_candidate_model(
            model_obj_or_path=deploy_model,
            config_obj_or_name=config,
            subject=sub,
            model_tag='candidate_1s'
        )
    else:
        print(f'[WARN] Deployment candidate model not found for {sub}: {deploy_model}')
"
```

### Step 3: Run Independent Verification on Exported Artifacts
Execute `validation.py` on each generated candidate model directory:
```bash
for sub in chb01 chb02 chb03; do
    echo "Testing artifact: experiments/window_alignment/artifacts/candidate_models/${sub}_candidate_1s"
    python3 experiments/window_alignment/code/validation.py --artifact-dir "experiments/window_alignment/artifacts/candidate_models/${sub}_candidate_1s"
done
```
**Acceptance Criterion:** Each candidate artifact must output:
`[PASS] All checks passed successfully!`
certifying that:
1. `weights.mem` has exactly 176 lines of 4-character hex.
2. `bias.mem` has exactly 1 line of 8-character hex.
3. `feature_order.json` covers 176 channel/subband/feature entries.
4. Independent 40-bit accumulator simulation reproduces `expected_scores.hex` and `expected_decisions.hex` bit-for-bit.

---

## 3. STRICT CONSTRAINTS & EVIDENCE HIERARCHY

You must uphold the project evidence hierarchy:
- **Floating-point model evaluation:** Mathematical reference.
- **Quantized software evaluation:** Floating simulation with integer rounding.
- **Bit-exact fixed-point reference evaluation:** Exact cycle-accurate integer simulation.
- **RTL simulation:** Verilog Icarus/Vivado simulation.
- **Physical FPGA validation:** Execution on real Spartan-7 silicon connected over physical UART.

**Strict Prohibition:**
Do NOT claim that passing software fixed-point simulation or mock UART demonstration constitutes physical FPGA validation. State clearly that candidate models are validated in bit-accurate simulation and ready for hardware synthesis.

---

## 4. REPORT DELIVERABLE REQUIRED

Upon completion of this prompt, report:
1. **Fixed-Point Evaluation Summary:**
   - Overall Decision Agreement (%) between Float and Fixed-Point across all evaluated windows.
   - Mean SQNR (dB) and Mean Absolute Score Error.
   - Comparison of detected seizures: Float Total vs. Fixed-Point Total.
   - Comparison of false alarms: Float Total vs. Fixed-Point Total.
2. **Exported Artifacts Certification:**
   - File listing and verification status for `chb01_candidate_1s`, `chb02_candidate_1s`, and `chb03_candidate_1s`.
3. **Transition Statement:** `PROMPT_02_FIXED_POINT_AND_FPGA_EXPORT COMPLETE. PROCEED TO PROMPT_03_FINAL_RESULTS_AND_HANDOFF`.
```
