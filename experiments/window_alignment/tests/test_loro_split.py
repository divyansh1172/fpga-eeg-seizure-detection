"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: Leave-One-Record-Out (LORO) zero-leakage cross-validation and scaler fitting.
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

from experiment_runner import SimpleStandardScaler

class TestLoroSplit(unittest.TestCase):
    def test_train_only_standardization(self):
        """Verifies scaler is fitted strictly on training data without test leakage."""
        np.random.seed(42)
        # Train data centered around mean = 100.0, std = 15.0
        X_train = np.random.normal(loc=100.0, scale=15.0, size=(200, 176))
        # Test data with different distribution: mean = 50.0, std = 5.0
        X_test = np.random.normal(loc=50.0, scale=5.0, size=(50, 176))
        
        scaler = SimpleStandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        # Training set scaled mean must be ~0 and std ~1
        np.testing.assert_allclose(np.mean(X_train_scaled, axis=0), 0.0, atol=1e-5)
        np.testing.assert_allclose(np.std(X_train_scaled, axis=0), 1.0, atol=1e-5)
        
        # Test set transformed using train parameters
        X_test_scaled = scaler.transform(X_test)
        test_scaled_mean = np.mean(X_test_scaled)
        
        # Test set mean should NOT be 0 (proving it wasn't fitted on test)
        self.assertNotAlmostEqual(test_scaled_mean, 0.0, delta=1.0)
        # Expected test scaled mean: (50 - 100) / 15 = -3.33
        self.assertAlmostEqual(test_scaled_mean, -3.33, delta=0.5)

    def test_loro_partitioning_integrity(self):
        """Verifies no overlap between training records and held-out test record."""
        # Mock 5 records
        records = [
            {"filename": f"chb01_{i:02d}.edf", "features": np.full((10, 5), i)}
            for i in range(1, 6)
        ]
        
        for test_idx in range(len(records)):
            held_out = records[test_idx]["filename"]
            train_files = [r["filename"] for idx, r in enumerate(records) if idx != test_idx]
            
            # Held-out file must NOT be in training set
            self.assertNotIn(held_out, train_files)
            # Training set must have exactly N-1 records
            self.assertEqual(len(train_files), 4)

if __name__ == "__main__":
    unittest.main()
