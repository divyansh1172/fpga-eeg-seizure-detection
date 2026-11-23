# Experiment Reports Directory

**Directory:** `experiments/window_alignment/reports/`

## Purpose
This directory stores all evaluation outputs, fold-level CSV files, summary metrics, and comparative analysis documents generated during cross-validation and fixed-point evaluation.

## Output Locations
- `window_1s_fpga_aligned/`:
  - `loro_folds.csv`: Detailed fold-by-fold results (all 47 folds) for Configuration A.
  - `summary_metrics.csv` & `summary_metrics.json`: Pooled subject-level and cohort-level event metrics.
  - `fixedpoint_comparison.csv`: Direct, empirical comparison between 64-bit float and bit-accurate fixed-point RTL performance.
- `window_2s_software_baseline/`:
  - `loro_folds.csv`: Detailed fold-by-fold results for Configuration B.
  - `summary_metrics.csv` & `summary_metrics.json`: Baseline performance summary.
- `comparison_1s_vs_2s.csv`: Side-by-side comparative table evaluating sensitivity, false alarm rate per hour, median latency, and window metrics between Configuration A and Configuration B.

## Metric Reporting Policy
Every percentage and rate reported must include exact denominators:
- Event Sensitivity: $X / Y$ detected clinical seizures.
- False Alarm Rate: $N\text{ false alarms} / H\text{ non-seizure recording hours}$.
- Latency: Reported as median and mean in seconds.
- Zero data fabrication: Results are only produced when actual model evaluation executes.
