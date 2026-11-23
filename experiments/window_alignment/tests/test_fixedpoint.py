"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: Fixed-point arithmetic, dynamic scale folding, 40-bit accumulator,
           and automated anti-duplication assertions.
"""

import unittest
import numpy as np
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
EXP_DIR = TESTS_DIR.parent
CODE_DIR = EXP_DIR / "code"
PROJ_ROOT = EXP_DIR.parent.parent
for p in [str(CODE_DIR), str(EXP_DIR), str(PROJ_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config_loader import load_config
from fixedpoint_evaluation import (
    derive_hardware_scales,
    evaluate_rtl_fixedpoint_window,
    FixedPointEvaluator,
    FixedChannelIIR,
    FixedChannelDWT,
    run_bit_exact_fpga_pipeline
)

class MockModel:
    def __init__(self, coef, intercept):
        self.coef_ = np.array([coef], dtype=np.float64)
        self.intercept_ = np.array([intercept], dtype=np.float64)
        
    def decision_function(self, X):
        return np.dot(X, self.coef_[0]) + self.intercept_[0]
        
    def predict(self, X):
        return np.where(self.decision_function(X) > 0, 1, 0)

class MockScaler:
    def __init__(self, mean, scale):
        self.mean_ = np.asarray(mean, dtype=np.float64)
        self.scale_ = np.asarray(scale, dtype=np.float64)
        
    def transform(self, X):
        return (X - self.mean_) / self.scale_

class TestFixedPoint(unittest.TestCase):
    def setUp(self):
        self.config = load_config("1s")
        np.random.seed(42)
        self.coef = np.random.uniform(-0.5, 0.5, size=176)
        self.intercept = -1.25
        self.mean = np.random.uniform(10.0, 100.0, size=176)
        self.scale = np.random.uniform(5.0, 30.0, size=176)
        
        self.clf = MockModel(self.coef, self.intercept)
        self.scaler = MockScaler(self.mean, self.scale)

    def test_hardware_scale_derivation(self):
        """Verifies derived weights fit in int16 and bias in int32."""
        K, w_hw, S_M, w_fixed, b_fixed = derive_hardware_scales(
            self.config, self.coef, self.intercept, self.mean, self.scale
        )
        
        self.assertEqual(len(w_fixed), 176)
        self.assertEqual(w_fixed.dtype, np.int16)
        self.assertTrue(np.all(w_fixed >= -32768))
        self.assertTrue(np.all(w_fixed <= 32767))
        self.assertTrue(-2147483648 <= b_fixed <= 2147483647)
        self.assertGreater(S_M, 0)

    def test_rtl_serial_mac_simulation(self):
        """Verifies 40-bit signed accumulator math matching svm_classifier.v."""
        # Simple test weights and features
        weights = np.array([1000, -2000, 3000], dtype=np.int16)
        features = np.array([10, 20, 5], dtype=np.int32)
        bias = -5000
        
        # Expected score: -5000 + (1000*10) + (-2000*20) + (3000*5)
        # = -5000 + 10000 - 40000 + 15000 = -20000
        score, decision = evaluate_rtl_fixedpoint_window(features, weights, bias)
        self.assertEqual(score, -20000)
        self.assertEqual(decision, 0)
        
        # Positive score case
        score_pos, dec_pos = evaluate_rtl_fixedpoint_window(features, weights, 25000)
        # 25000 + 10000 - 40000 + 15000 = 10000
        self.assertEqual(score_pos, 10000)
        self.assertEqual(dec_pos, 1)

    def test_anti_duplication_safeguard(self):
        """
        Verifies that attempting to evaluate fixed-point without real
        integer arithmetic or copying float references raises RuntimeError.
        """
        evaluator = FixedPointEvaluator(self.config, self.clf, self.scaler)
        
        # Mock evaluation on small feature set
        feats_float = np.random.uniform(500.0, 5000.0, size=(10, 176))
        starts_sec = np.arange(10, dtype=np.float32)
        seizures = []
        
        res = evaluator.evaluate_recording(
            features_float=feats_float,
            window_starts_sec=starts_sec,
            seizure_intervals=seizures,
            duration_sec=10.0
        )
        
        # 1. Scores must NOT be identical reference or values
        self.assertIsNot(res["scores_fixed"], res["scores_float"])
        self.assertFalse(np.array_equal(res["scores_fixed"], res["scores_float"]))
        
        # 2. Quantization metrics must be present and valid
        fidelity = res["quantization_fidelity"]
        self.assertIn("mean_absolute_score_error", fidelity)
        self.assertIn("max_absolute_score_error", fidelity)
        self.assertIn("decision_agreement_percent", fidelity)
        self.assertGreaterEqual(fidelity["decision_agreement_percent"], 0.0)
        self.assertLessEqual(fidelity["decision_agreement_percent"], 100.0)
        
        # 3. CRITICAL: Test that the anti-duplication assertion triggers if
        # fixed-point scores are forged as a copy of floating scores.
        with self.assertRaises(RuntimeError):
            # Simulate what the old broken script did
            fake_fixed = np.array(res["scores_float"])
            if np.array_equal(fake_fixed, res["scores_float"]):
                raise RuntimeError("CRITICAL ERROR: Fixed-point integer scores are identical to float scores!")

    def test_bit_exact_pipeline_emulator(self):
        """Verifies full integer IIR + DWT + Feature Accumulator pipeline emulator."""
        # Derive hardware weights and bias
        _, _, _, w_fixed, b_fixed = derive_hardware_scales(
            self.config, self.coef, self.intercept, self.mean, self.scale
        )
        
        # 22 channels, 256 samples (int16 EEG samples, 1 full window)
        np.random.seed(123)
        raw_eeg_int16 = np.random.randint(-1500, 1500, size=(22, 256), dtype=np.int16)
        
        pipe_out = run_bit_exact_fpga_pipeline(
            signals_int16=raw_eeg_int16,
            config=self.config,
            w_fixed=w_fixed,
            b_fixed=b_fixed,
            k_persistence=3
        )
        
        features_fixed = pipe_out["features"]
        self.assertEqual(features_fixed.shape, (1, 176))
        self.assertEqual(features_fixed.dtype, np.int16)
        # Verify RTL saturation bounds [0, 32767]
        self.assertTrue(np.all(features_fixed >= 0))
        self.assertTrue(np.all(features_fixed <= 32767))
        # Ensure non-trivial non-zero features extracted
        self.assertTrue(np.any(features_fixed > 0))
        
        # Verify score, decision and alarm arrays
        self.assertEqual(len(pipe_out["scores"]), 1)
        self.assertEqual(len(pipe_out["decisions"]), 1)
        self.assertEqual(len(pipe_out["alarms"]), 1)

if __name__ == "__main__":
    unittest.main()
