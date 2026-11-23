#!/usr/bin/env python3
"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Script: experiments/window_alignment/tests/run_tests.py
Purpose: Single regression entry point executing all infrastructure tests
         with automated PASS/FAIL reporting.
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

def run_all_tests():
    print("================================================================================")
    print(" EE2000 FPGA Seizure Detector — Experiment Infrastructure Test Regression")
    print(" Target: Python 3.x / Pure NumPy & SciPy Verification Suite")
    print("================================================================================")
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(TESTS_DIR), pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n================================================================================")
    print(" INFRASTRUCTURE REGRESSION SUMMARY")
    print("================================================================================")
    print(f" Tests Run:   {result.testsRun}")
    print(f" Failures:    {len(result.failures)}")
    print(f" Errors:      {len(result.errors)}")
    print(f" Total Green: {result.testsRun - len(result.failures) - len(result.errors)} / {result.testsRun}")
    
    if result.wasSuccessful():
        print(" OVERALL STATUS: ALL INFRASTRUCTURE TESTS PASSED (100% GREEN)")
        print("================================================================================")
        return 0
    else:
        print(" OVERALL STATUS: REGRESSION FAILED")
        print("================================================================================")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
