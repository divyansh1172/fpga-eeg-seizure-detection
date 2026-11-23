"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Unit Test: Actual RTL Co-Simulation of svm_classifier.v using Icarus Verilog (iverilog/vvp).
           Generates deterministic edge-case test vectors (positive, negative, near-zero,
           and boundary/overflow cases), feeds them to real Verilog RTL, captures hardware
           outputs, and compares against Python reference bit-for-bit.
"""

import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np

TESTS_DIR = Path(__file__).resolve().parent
EXP_DIR = TESTS_DIR.parent
PROJ_ROOT = EXP_DIR.parent.parent
RTL_DIR = PROJ_ROOT / "rtl"

class TestRTLCosimulation(unittest.TestCase):
    def setUp(self):
        self.iverilog_bin = shutil.which("iverilog")
        self.vvp_bin = shutil.which("vvp")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="svm_cosim_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_svm_classifier_verilog_cosim(self):
        """Compiles and co-simulates svm_classifier.v with iverilog."""
        if not self.iverilog_bin or not self.vvp_bin:
            self.skipTest("Icarus Verilog (iverilog/vvp) not found in system PATH.")

        # =====================================================================
        # 1. Construct Deterministic Test Cases (176 Features each)
        # =====================================================================
        test_cases = []

        # Case 1: Standard Positive Score (Ictal Detection)
        w1 = np.full(176, 100, dtype=np.int16)
        f1 = np.full(176, 50, dtype=np.int16)
        b1 = -200000  # sum = 176 * 5000 = 880,000 -> score = 680,000 > 0
        test_cases.append({"name": "Standard Positive", "w": w1, "f": f1, "b": b1})

        # Case 2: Standard Negative Score (Interictal Background)
        w2 = np.full(176, -50, dtype=np.int16)
        f2 = np.full(176, 100, dtype=np.int16)
        b2 = -100000  # sum = 176 * -5000 = -880,000 -> score = -980,000 < 0
        test_cases.append({"name": "Standard Negative", "w": w2, "f": f2, "b": b2})

        # Case 3: Near-Zero Boundary (+1)
        # b = +1, all w = 0, all f = 0 -> score = +1 -> decision = 1
        w3 = np.zeros(176, dtype=np.int16)
        f3 = np.zeros(176, dtype=np.int16)
        b3 = 1
        test_cases.append({"name": "Near-Zero Positive (+1)", "w": w3, "f": f3, "b": b3})

        # Case 4: Near-Zero Boundary (-1)
        # b = -1, all w = 0, all f = 0 -> score = -1 -> decision = 0
        w4 = np.zeros(176, dtype=np.int16)
        f4 = np.zeros(176, dtype=np.int16)
        b4 = -1
        test_cases.append({"name": "Near-Zero Negative (-1)", "w": w4, "f": f4, "b": b4})

        # Case 5: Zero Boundary (Score == 0)
        # b = 0, all w = 0, all f = 0 -> score = 0 -> decision = 0 (RTL: score > 0 ? 1 : 0)
        w5 = np.zeros(176, dtype=np.int16)
        f5 = np.zeros(176, dtype=np.int16)
        b5 = 0
        test_cases.append({"name": "Exact Zero Boundary", "w": w5, "f": f5, "b": b5})

        # Case 6: Near-Zero Cancelled Sum (+1 via dot product)
        # b = -999, feature 0 = 1000, weight 0 = 1, all others 0 -> score = +1 -> decision = 1
        w6 = np.zeros(176, dtype=np.int16)
        w6[0] = 1
        f6 = np.zeros(176, dtype=np.int16)
        f6[0] = 1000
        b6 = -999
        test_cases.append({"name": "Cancelled Sum (+1)", "w": w6, "f": f6, "b": b6})

        # Case 7: Maximum Positive Boundary
        # Max positive features (32767) x max positive weights (32767)
        # Prod = 1,073,676,289 per feature x 176 = 188,967,026,864 (fits within 40-bit signed: max ~549 billion)
        w7 = np.full(176, 32767, dtype=np.int16)
        f7 = np.full(176, 32767, dtype=np.int16)
        b7 = 2147483647  # Max int32
        test_cases.append({"name": "Max Positive 40-Bit", "w": w7, "f": f7, "b": b7})

        # Case 8: Maximum Negative Boundary
        # Max positive features (32767) x min negative weights (-32768)
        # Prod = -1,073,741,824 x 176 = -188,978,561,024
        w8 = np.full(176, -32768, dtype=np.int16)
        f8 = np.full(176, 32767, dtype=np.int16)
        b8 = -2147483648  # Min int32
        test_cases.append({"name": "Max Negative 40-Bit", "w": w8, "f": f8, "b": b8})

        # Case 9: Physiological Mock Vector
        np.random.seed(999)
        w9 = np.random.randint(-1500, 1500, size=176, dtype=np.int16)
        f9 = np.random.randint(0, 15000, size=176, dtype=np.int16)
        b9 = -771706  # Matches existing SVM_BIAS_EFF
        test_cases.append({"name": "Physiological Mock", "w": w9, "f": f9, "b": b9})

        # =====================================================================
        # 2. Compute Expected Golden Scores and Decisions in Python (40-bit signed)
        # =====================================================================
        for tc in test_cases:
            accum = np.int64(tc["b"])
            for feat_val, weight_val in zip(tc["f"], tc["w"]):
                accum += np.int64(feat_val) * np.int64(weight_val)
            tc["expected_score"] = int(accum)
            tc["expected_decision"] = 1 if accum > 0 else 0

        # =====================================================================
        # 3. Write Stimulus Hex Files for Verilog Testbench
        # =====================================================================
        # For simplicity in tb_svm_cosim, we test each case in sequence by running
        # a dedicated simulation pass per unique (w, b) or by feeding test cases.
        # Let's test all cases in a unified testbench execution.
        # Notice: In tb_svm_cosim, weight_rom and bias_rom are shared across windows in one run,
        # or we can test multiple windows with shared weights/bias, OR test each case individually.
        # Testing each case individually guarantees test isolation for weights, bias and features!

        dut_src = RTL_DIR / "svm_classifier.v"
        tb_src = TESTS_DIR / "tb_svm_cosim.v"
        sim_bin = self.temp_dir / "sim_svm_cosim"

        # Compile Verilog RTL and testbench once
        cmd_compile = [
            self.iverilog_bin,
            "-g2001",
            "-Wall",
            "-o", str(sim_bin),
            str(dut_src),
            str(tb_src)
        ]
        res_compile = subprocess.run(cmd_compile, capture_output=True, text=True)
        self.assertEqual(res_compile.returncode, 0, f"iverilog compilation failed:\n{res_compile.stderr}")

        # Run each test case through the RTL simulator
        for idx, tc in enumerate(test_cases):
            # Write stimulus files in temp_dir
            with open(self.temp_dir / "cosim_weights.hex", "w") as f:
                for val in tc["w"]:
                    f.write(f"{int(val) & 0xFFFF:04X}\n")

            with open(self.temp_dir / "cosim_bias.hex", "w") as f:
                f.write(f"{int(tc['b']) & 0xFFFFFFFF:08X}\n")

            with open(self.temp_dir / "cosim_features.hex", "w") as f:
                for val in tc["f"]:
                    f.write(f"{int(val) & 0xFFFF:04X}\n")

            with open(self.temp_dir / "cosim_control.hex", "w") as f:
                f.write(f"{1:08X}\n") # 1 window

            # Execute simulation in temp_dir
            cmd_sim = [self.vvp_bin, str(sim_bin)]
            res_sim = subprocess.run(cmd_sim, cwd=self.temp_dir, capture_output=True, text=True)
            self.assertEqual(res_sim.returncode, 0, f"Simulation runtime error on {tc['name']}:\n{res_sim.stderr}")

            # Read cosim_results.hex
            res_file = self.temp_dir / "cosim_results.hex"
            self.assertTrue(res_file.is_file(), f"cosim_results.hex not generated for {tc['name']}")

            with open(res_file, "r") as f:
                lines = [l.strip() for l in f if l.strip()]

            self.assertEqual(len(lines), 1, f"Expected 1 result line, got {len(lines)}")
            hex_score_str, dec_str = lines[0].split()

            # Parse 40-bit signed hex output
            u40_score = int(hex_score_str, 16)
            rtl_score = u40_score if u40_score < (1 << 39) else u40_score - (1 << 40)
            rtl_decision = int(dec_str)

            # Assert Bit-Exact Match between RTL Hardware and Python Reference
            self.assertEqual(
                rtl_score,
                tc["expected_score"],
                f"[{tc['name']}] RTL score ({rtl_score}) != Python expected ({tc['expected_score']})"
            )
            self.assertEqual(
                rtl_decision,
                tc["expected_decision"],
                f"[{tc['name']}] RTL decision ({rtl_decision}) != Python expected ({tc['expected_decision']})"
            )

        print(f"\n[OK] RTL Co-Simulation PASSED: All {len(test_cases)} edge cases matched Spartan-7 RTL bit-for-bit!")

if __name__ == "__main__":
    unittest.main()
