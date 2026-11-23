"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: DWT decomposition, subband extraction, 176-feature dimension and ordering.
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

from feature_pipeline import (
    compute_dwt_5levels_1d,
    extract_subband_features,
    extract_window_features_176
)

class TestFeatures(unittest.TestCase):
    def test_dwt_dyadic_lengths_256(self):
        """Checks dyadic subband lengths for 256-sample (1.0s) window."""
        x = np.random.randn(256)
        subbands = compute_dwt_5levels_1d(x)
        
        self.assertIn("D3", subbands)
        self.assertIn("D4", subbands)
        self.assertIn("D5", subbands)
        self.assertIn("A5", subbands)
        
        # Expected lengths for 1.0s window:
        self.assertEqual(len(subbands["D3"]), 32)
        self.assertEqual(len(subbands["D4"]), 16)
        self.assertEqual(len(subbands["D5"]), 8)
        self.assertEqual(len(subbands["A5"]), 8)

    def test_dwt_dyadic_lengths_512(self):
        """Checks dyadic subband lengths for 512-sample (2.0s) window."""
        x = np.random.randn(512)
        subbands = compute_dwt_5levels_1d(x)
        
        # Expected lengths for 2.0s window:
        self.assertEqual(len(subbands["D3"]), 64)
        self.assertEqual(len(subbands["D4"]), 32)
        self.assertEqual(len(subbands["D5"]), 16)
        self.assertEqual(len(subbands["A5"]), 16)

    def test_energy_and_linelength_math(self):
        """Verifies deterministic math for Energy and Line-Length."""
        # Simple test vector: [1, 3, 5, 7]
        # Energy = (1^2 + 3^2 + 5^2 + 7^2) / 4 = (1 + 9 + 25 + 49) / 4 = 84 / 4 = 21.0
        # Line-Length = (|3-1| + |5-3| + |7-5|) / 3 = (2 + 2 + 2) / 3 = 2.0
        vec = np.array([1.0, 3.0, 5.0, 7.0])
        e, ll = extract_subband_features(vec)
        self.assertAlmostEqual(e, 21.0, places=5)
        self.assertAlmostEqual(ll, 2.0, places=5)

    def test_feature_vector_dimension_176(self):
        """Verifies multi-channel window produces exactly 176 features."""
        # 22 channels, 256 samples
        w_sig = np.random.randn(22, 256).astype(np.float32)
        feats = extract_window_features_176(w_sig)
        
        self.assertEqual(feats.shape, (176,))
        self.assertTrue(np.all(np.isfinite(feats)))
        # Non-negative energy and line-length
        self.assertTrue(np.all(feats >= 0.0))

if __name__ == "__main__":
    unittest.main()
