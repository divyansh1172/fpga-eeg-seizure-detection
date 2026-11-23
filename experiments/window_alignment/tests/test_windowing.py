"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: Window generation, hop calculations, boundary enforcement, and label alignment.
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

from feature_pipeline import generate_window_slices

class TestWindowing(unittest.TestCase):
    def setUp(self):
        self.fs = 256
        # 10 seconds of synthetic data = 2560 samples
        self.duration_sec = 10.0
        self.num_samples = int(self.duration_sec * self.fs)
        # Seizure interval from 3.0s to 5.2s (duration 2.2s)
        self.seizures = [(3.0, 5.2)]

    def test_window_1s_non_overlapping(self):
        """Configuration A: 1.0s window, 1.0s hop (256 samples, no overlap)."""
        w_samp = 256
        h_samp = 256
        starts_samp, starts_sec, labels = generate_window_slices(
            num_samples=self.num_samples,
            window_samples=w_samp,
            hop_samples=h_samp,
            fs=self.fs,
            seizure_intervals=self.seizures,
            label_overlap_thresh=0.5
        )
        
        # 10 full 1-second windows in 10 seconds
        self.assertEqual(len(starts_samp), 10)
        self.assertEqual(len(labels), 10)
        # Check boundary handling: last window ends at sample 2560
        self.assertEqual(starts_samp[-1] + w_samp, self.num_samples)
        # Check hop step
        np.testing.assert_array_equal(np.diff(starts_samp), 256)
        
        # Check label alignment:
        # Seizure is 3.0 to 5.2 s.
        # Window [2.0, 3.0): overlap 0s -> 0
        # Window [3.0, 4.0): overlap 1.0s / 1.0s = 100% >= 50% -> 1
        # Window [4.0, 5.0): overlap 1.0s / 1.0s = 100% >= 50% -> 1
        # Window [5.0, 6.0): overlap 0.2s / 1.0s = 20% < 50% -> 0
        expected_labels = [0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
        np.testing.assert_array_equal(labels, expected_labels)

    def test_window_2s_overlapping(self):
        """Configuration B: 2.0s window, 1.0s hop (512 samples, 50% overlap)."""
        w_samp = 512
        h_samp = 256
        starts_samp, starts_sec, labels = generate_window_slices(
            num_samples=self.num_samples,
            window_samples=w_samp,
            hop_samples=h_samp,
            fs=self.fs,
            seizure_intervals=self.seizures,
            label_overlap_thresh=0.5
        )
        
        # In 10s (2560 samples), possible 2s windows with 1s hop:
        # starts at 0, 1, 2, 3, 4, 5, 6, 7, 8 s -> 9 windows
        self.assertEqual(len(starts_samp), 9)
        # Check boundary: last window starts at 8s, ends at 10s (2560 samples)
        self.assertEqual(starts_samp[-1] + w_samp, self.num_samples)
        
        # Label check:
        # Window [2.0, 4.0): overlap [3.0, 4.0) = 1.0s / 2.0s = 50% >= 50% -> 1
        # Window [3.0, 5.0): overlap [3.0, 5.0) = 2.0s / 2.0s = 100% >= 50% -> 1
        # Window [4.0, 6.0): overlap [4.0, 5.2) = 1.2s / 2.0s = 60% >= 50% -> 1
        # Window [5.0, 7.0): overlap [5.0, 5.2) = 0.2s / 2.0s = 10% < 50% -> 0
        expected_labels = [0, 0, 1, 1, 1, 0, 0, 0, 0]
        np.testing.assert_array_equal(labels, expected_labels)

    def test_short_recording_handling(self):
        """Recordings shorter than one window return empty arrays without crashing."""
        starts_samp, starts_sec, labels = generate_window_slices(
            num_samples=200,
            window_samples=256,
            hop_samples=256,
            fs=self.fs
        )
        self.assertEqual(len(starts_samp), 0)
        self.assertEqual(len(labels), 0)

if __name__ == "__main__":
    unittest.main()
