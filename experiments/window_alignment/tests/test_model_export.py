"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: FPGA model candidate export, .mem file formatting, and independent validation.
"""

import unittest
import numpy as np
import tempfile
import shutil
import re
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
from model_export import export_candidate_model
from validation import validate_candidate_directory

class MockModel:
    def __init__(self, coef, intercept):
        self.coef_ = np.array([coef], dtype=np.float64)
        self.intercept_ = np.array([intercept], dtype=np.float64)

class MockScaler:
    def __init__(self, mean, scale):
        self.mean_ = np.asarray(mean, dtype=np.float64)
        self.scale_ = np.asarray(scale, dtype=np.float64)

class TestModelExport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_fpga_export_"))
        self.config = load_config("1s")
        np.random.seed(123)
        self.coef = np.random.uniform(-0.4, 0.4, size=176)
        self.intercept = -2.5
        self.mean = np.random.uniform(50.0, 200.0, size=176)
        self.scale = np.random.uniform(10.0, 50.0, size=176)
        
        self.model_data = {
            "clf": MockModel(self.coef, self.intercept),
            "scaler": MockScaler(self.mean, self.scale),
            "is_deployment_candidate": True
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_and_validate(self):
        """Exports candidate model to temporary dir and runs full validation suite."""
        out_dir = export_candidate_model(
            model_obj_or_path=self.model_data,
            config_obj_or_name=self.config,
            subject="chb01",
            model_tag="unit_test_candidate",
            out_dir=self.temp_dir
        )
        
        # Check files created
        self.assertTrue((out_dir / "weights.mem").is_file())
        self.assertTrue((out_dir / "bias.mem").is_file())
        self.assertTrue((out_dir / "model_metadata.json").is_file())
        self.assertTrue((out_dir / "feature_order.json").is_file())
        self.assertTrue((out_dir / "expected_features.hex").is_file())
        self.assertTrue((out_dir / "expected_scores.hex").is_file())
        self.assertTrue((out_dir / "expected_decisions.hex").is_file())
        
        # Verify weights.mem: exactly 176 lines, 4-char hex
        with open(out_dir / "weights.mem") as wf:
            lines = [l.strip() for l in wf if l.strip()]
        self.assertEqual(len(lines), 176)
        for line in lines:
            self.assertTrue(bool(re.match(r"^[0-9A-Fa-f]{4}$", line)))
            
        # Verify bias.mem: exactly 1 line, 8-char hex
        with open(out_dir / "bias.mem") as bf:
            b_lines = [l.strip() for l in bf if l.strip()]
        self.assertEqual(len(b_lines), 1)
        self.assertTrue(bool(re.match(r"^[0-9A-Fa-f]{8}$", b_lines[0])))
        
        # Run independent validation module
        val_result = validate_candidate_directory(out_dir)
        self.assertEqual(val_result["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
