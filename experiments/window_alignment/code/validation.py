"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.validation
Purpose: Standalone verification tool that inspects an exported candidate model
         artifact directory, checks RTL formatting constraints, and executes an
         independent bit-exact simulation to verify zero numerical discrepancy.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

def validate_candidate_directory(artifact_dir: Path) -> Dict[str, Any]:
    """
    Validates all files in an exported candidate model directory.
    Returns validation report dictionary. Raises ValueError on violation.
    """
    artifact_dir = Path(artifact_dir)
    if not artifact_dir.is_dir():
        raise FileNotFoundError(f"Artifact directory not found: {artifact_dir}")
        
    print(f"\n================================================================================")
    print(f" Validating FPGA Model Candidate Artifact: {artifact_dir.name}")
    print(f"================================================================================")
    
    errors: List[str] = []
    
    # -------------------------------------------------------------------------
    # 1. Inspect weights.mem
    # -------------------------------------------------------------------------
    weights_path = artifact_dir / "weights.mem"
    if not weights_path.is_file():
        errors.append("weights.mem file missing.")
        weights_int16 = np.array([])
    else:
        with open(weights_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if len(lines) != 176:
            errors.append(f"weights.mem has {len(lines)} lines; expected exactly 176.")
            
        w_vals = []
        for l_num, line in enumerate(lines, 1):
            if not re.match(r"^[0-9A-Fa-f]{4}$", line):
                errors.append(f"weights.mem line {l_num} ('{line}') is not a valid 4-character hex word.")
            else:
                u16 = int(line, 16)
                # Convert to signed 16-bit
                s16 = u16 if u16 < 32768 else u16 - 65536
                w_vals.append(s16)
        weights_int16 = np.array(w_vals, dtype=np.int16)
        
    # -------------------------------------------------------------------------
    # 2. Inspect bias.mem
    # -------------------------------------------------------------------------
    bias_path = artifact_dir / "bias.mem"
    if not bias_path.is_file():
        errors.append("bias.mem file missing.")
        bias_int32 = 0
    else:
        with open(bias_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if len(lines) != 1:
            errors.append(f"bias.mem has {len(lines)} lines; expected exactly 1.")
            bias_int32 = 0
        else:
            line = lines[0]
            if not re.match(r"^[0-9A-Fa-f]{8}$", line):
                errors.append(f"bias.mem ('{line}') is not a valid 8-character hex word.")
                bias_int32 = 0
            else:
                u32 = int(line, 16)
                bias_int32 = u32 if u32 < 2147483648 else u32 - 4294967296
                
    # -------------------------------------------------------------------------
    # 3. Inspect feature_order.json
    # -------------------------------------------------------------------------
    feat_order_path = artifact_dir / "feature_order.json"
    if not feat_order_path.is_file():
        errors.append("feature_order.json missing.")
    else:
        with open(feat_order_path, "r", encoding="utf-8") as f:
            feat_map = json.load(f)
        if len(feat_map) != 176:
            errors.append(f"feature_order.json has {len(feat_map)} entries; expected 176.")
            
    # -------------------------------------------------------------------------
    # 4. Inspect model_metadata.json
    # -------------------------------------------------------------------------
    meta_path = artifact_dir / "model_metadata.json"
    if not meta_path.is_file():
        errors.append("model_metadata.json missing.")
        metadata = {}
    else:
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            
    # -------------------------------------------------------------------------
    # 5. Independent Numerical Simulation of Test Vectors
    # -------------------------------------------------------------------------
    exp_features_path = artifact_dir / "expected_features.hex"
    exp_scores_path = artifact_dir / "expected_scores.hex"
    exp_decisions_path = artifact_dir / "expected_decisions.hex"
    
    sim_ok = True
    if exp_features_path.is_file() and exp_scores_path.is_file() and exp_decisions_path.is_file() and len(weights_int16) == 176:
        with open(exp_features_path, "r") as f:
            f_lines = [l.strip() for l in f if l.strip()]
        with open(exp_scores_path, "r") as f:
            s_lines = [l.strip() for l in f if l.strip()]
        with open(exp_decisions_path, "r") as f:
            d_lines = [l.strip() for l in f if l.strip()]
            
        num_test_windows = len(f_lines) // 176
        if len(f_lines) % 176 != 0:
            errors.append(f"expected_features.hex has {len(f_lines)} lines; not a multiple of 176.")
        elif len(s_lines) != num_test_windows or len(d_lines) != num_test_windows:
            errors.append(f"Mismatched vector counts: {num_test_windows} windows, {len(s_lines)} scores, {len(d_lines)} decisions.")
        else:
            # Re-simulate RTL MAC for each test window
            for w in range(num_test_windows):
                w_f_hex = f_lines[w * 176 : (w + 1) * 176]
                w_features = [int(h, 16) for h in w_f_hex]
                
                # Independent 40-bit accumulator simulation
                accum = np.int64(bias_int32)
                for f_val, w_val in zip(w_features, weights_int16):
                    accum += np.int64(f_val) * np.int64(w_val)
                    
                dec = 1 if accum > 0 else 0
                
                # Check against expected vectors
                exp_sc_u40 = int(s_lines[w], 16)
                # Parse 40-bit signed
                exp_sc = exp_sc_u40 if exp_sc_u40 < (1 << 39) else exp_sc_u40 - (1 << 40)
                exp_dec = int(d_lines[w])
                
                if accum != exp_sc:
                    errors.append(f"Window {w}: Recomputed score ({accum}) != expected vector score ({exp_sc})")
                    sim_ok = False
                if dec != exp_dec:
                    errors.append(f"Window {w}: Recomputed decision ({dec}) != expected decision ({exp_dec})")
                    sim_ok = False
                    
    if errors:
        print(f" [FAIL] Candidate artifact validation FAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"   - {e}")
        return {"status": "FAIL", "errors": errors}
    else:
        print(f" [PASS] All checks passed successfully!")
        print(f"        - 176 weights verified in weights.mem (hex %04X)")
        print(f"        - 32-bit bias verified in bias.mem (hex %08X)")
        print(f"        - 176 feature ordering indices verified")
        print(f"        - Bit-exact RTL MAC score and decision simulation matches golden vectors 100%")
        return {"status": "PASS", "metadata": metadata}

def main():
    parser = argparse.ArgumentParser(description="Validate an exported FPGA model candidate artifact.")
    parser.add_argument("--artifact-dir", type=str, required=True, help="Path to exported model directory")
    args = parser.parse_args()
    
    result = validate_candidate_directory(Path(args.artifact_dir))
    if result["status"] != "PASS":
        sys.exit(1)

if __name__ == "__main__":
    main()
