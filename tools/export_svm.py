#!/usr/bin/env python3
"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Script: tools/export_svm.py
Purpose: Exports trained Linear SVM weights and folded bias to Verilog memory
         initialization hex files (weights.mem, bias.mem) for FPGA inference.
         Applies hardware dynamic scale folding:
           w_hw = (coef / scale) * K_feat
           b_eff = intercept - sum((coef * mean) / scale)
           S_M = max integer multiplier fitting w_hw in int16
           w_fixed = round(w_hw * S_M) in signed int16
           b_fixed = round(b_eff * S_M) in signed int32
"""

import sys
import pickle
from pathlib import Path
import numpy as np

PROJ_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJ_ROOT / "golden"
VECTORS_DIR = GOLDEN_DIR / "vectors"

NUM_CHANNELS = 22
RETAINED_BANDS = ["D3", "D4", "D5", "A5"]
NUM_SUBBANDS = len(RETAINED_BANDS)
TOTAL_FEATS = NUM_CHANNELS * NUM_SUBBANDS * 2  # 176

COEFF_COUNTS = {"D3": 32, "D4": 16, "D5": 8, "A5": 8}
ENERGY_SHIFTS = {"D3": 20, "D4": 19, "D5": 18, "A5": 18}
LINELENGTH_SHIFTS = {"D3": 5, "D4": 4, "D5": 3, "A5": 3}
S_SIG = 20.0  # 20 LSB / uV

class Dummy:
    def __init__(self, *args, **kwargs): pass
    def __setstate__(self, state): self.__dict__.update(state)

class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if "sklearn" in module:
            return Dummy
        return super().find_class(module, name)

def load_svm_model(subject: str = "chb01"):
    model_path = PROJ_ROOT / "results" / "models" / f"{subject}_fold0_model.pkl"
    npy_w = GOLDEN_DIR / f"w_eff_{subject}.npy"
    npy_b = GOLDEN_DIR / f"b_eff_{subject}.npy"

    if npy_w.exists() and npy_b.exists():
        w_eff = np.load(npy_w)
        b_eff = float(np.load(npy_b)[0])
        print(f"[LOAD] Loaded precomputed effective weights from {npy_w}")
        return w_eff, b_eff

    if not model_path.exists():
        raise FileNotFoundError(f"Model file {model_path} not found!")

    with open(model_path, "rb") as f:
        m = SafeUnpickler(f).load()

    coef = m["clf"].coef_[0]
    intercept = m["clf"].intercept_[0]
    mean = m["scaler"].mean_
    scale = m["scaler"].scale_

    w_eff = coef / scale
    b_eff = float(intercept - np.sum(coef * mean / scale))

    np.save(npy_w, w_eff)
    np.save(npy_b, np.array([b_eff]))
    print(f"[LOAD] Extracted w_eff, b_eff from {model_path}")
    return w_eff, b_eff

def compute_scales(w_eff: np.ndarray, b_eff: float):
    K = []
    for ch in range(NUM_CHANNELS):
        for b in RETAINED_BANDS:
            Nb = COEFF_COUNTS[b]
            k_e = (2.0 ** ENERGY_SHIFTS[b]) / ((S_SIG ** 2.0) * float(Nb))
            k_ll = (2.0 ** LINELENGTH_SHIFTS[b]) / (S_SIG * float(Nb - 1))
            K.extend([k_e, k_ll])
    K = np.array(K, dtype=np.float64)

    w_hw = w_eff * K
    max_w = np.max(np.abs(w_hw))
    S_M = int(32767.0 / (max_w * 1.05))

    w_fixed = np.clip(np.round(w_hw * S_M), -32768, 32767).astype(np.int16)
    b_fixed = int(round(b_eff * S_M))

    return K, S_M, w_fixed, b_fixed

def export_weights(w_fixed: np.ndarray, b_fixed: int, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    w_file = out_dir / "weights.mem"
    b_file = out_dir / "bias.mem"

    with open(w_file, "w") as f:
        for val in w_fixed:
            f.write(f"{int(val) & 0xFFFF:04X}\n")

    with open(b_file, "w") as f:
        f.write(f"{int(b_fixed) & 0xFFFFFFFF:08X}\n")

    print(f"[EXPORT] Wrote {len(w_fixed)} weights to {w_file}")
    print(f"[EXPORT] Wrote 32-bit bias ({b_fixed} = 0x{b_fixed & 0xFFFFFFFF:08X}) to {b_file}")

def main():
    print("=" * 80)
    print(" EE2000 SVM Model Quantization & Hardware Memory Exporter")
    print("=" * 80)
    w_eff, b_eff = load_svm_model("chb01")
    K, S_M, w_fixed, b_fixed = compute_scales(w_eff, b_eff)

    print(f"\nModel Parameters:")
    print(f"  Effective Weight Vector: len={len(w_eff)}, min={w_eff.min():.5f}, max={w_eff.max():.5f}")
    print(f"  Effective Bias b_eff:    {b_eff:.5f}")
    print(f"  Hardware Multiplier S_M: {S_M}")
    print(f"  Quantized Weights (Q15): min={w_fixed.min()}, max={w_fixed.max()}")
    print(f"  Quantized Bias (int32):  {b_fixed} (0x{b_fixed & 0xFFFFFFFF:08X})")

    # Export to golden/vectors/ and root
    export_weights(w_fixed, b_fixed, VECTORS_DIR)
    export_weights(w_fixed, b_fixed, PROJ_ROOT)

    print("\n[OK] Model export complete and verified!")

if __name__ == "__main__":
    main()
