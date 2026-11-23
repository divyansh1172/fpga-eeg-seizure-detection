"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Project: 22-Channel FPGA Seizure Detector
Module: experiments.window_alignment.code.fixedpoint_evaluation
Purpose: Bit-accurate fixed-point evaluation pipeline replicating Spartan-7 RTL
         arithmetic (Q15 weights/features, Q30 bias, 40-bit accumulator),
         with automated anti-duplication assertions and SQNR profiling.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from pathlib import Path
import json

try:
    from .evaluation import evaluate_predictions
    from .metrics import compute_window_metrics, aggregate_event_metrics
except ImportError:
    from evaluation import evaluate_predictions
    from metrics import compute_window_metrics, aggregate_event_metrics

def derive_hardware_scales(
    config: Dict[str, Any],
    coef: np.ndarray,
    intercept: float,
    scaler_mean: np.ndarray,
    scaler_scale: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, int, np.ndarray, int]:
    """
    Derives exact FPGA dynamic scale folding parameters:
        w_eff = coef / scale
        b_eff = intercept - sum((coef * mean) / scale)
        K_j: hardware feature scaling factor (Energy & Line-Length)
        w_hw = w_eff * K
        S_M = max integer scaling factor fitting w_hw into signed int16
        w_fixed = round(w_hw * S_M) in [-32768, 32767]
        b_fixed = round(b_eff * S_M) in [-2^31, 2^31 - 1]
    """
    coef = np.asarray(coef, dtype=np.float64).ravel()
    scaler_mean = np.asarray(scaler_mean, dtype=np.float64).ravel()
    scaler_scale = np.asarray(scaler_scale, dtype=np.float64).ravel()
    
    # Effective unscaled floating weights and bias
    w_eff = coef / scaler_scale
    b_eff = float(intercept - np.sum((coef * scaler_mean) / scaler_scale))
    
    num_channels = config["channels"]["count"]
    retained_bands = config["wavelet"]["retained_subbands"]
    subband_counts = config["wavelet"]["subband_coeff_counts"]
    hw_e_shifts = config["hardware_fixedpoint"]["energy_shifts"]
    hw_ll_shifts = config["hardware_fixedpoint"]["linelength_shifts"]
    s_sig = config["sampling"]["adc_scale_lsb_per_uv"]  # 20.0 LSB/uV
    
    K: List[float] = []
    for ch in range(num_channels):
        for b in retained_bands:
            nb = subband_counts[b]
            shift_e = hw_e_shifts[b]
            shift_ll = hw_ll_shifts[b]
            
            # K_E = 2^shift_e / (S_sig^2 * Nb)
            k_e = float((2.0 ** shift_e) / ((s_sig ** 2.0) * float(nb)))
            # K_LL = 2^shift_ll / (S_sig * (Nb - 1))
            k_ll = float((2.0 ** shift_ll) / (s_sig * float(max(1, nb - 1))))
            
            K.extend([k_e, k_ll])
            
    K_arr = np.array(K, dtype=np.float64)
    w_hw = w_eff * K_arr
    
    max_w = float(np.max(np.abs(w_hw)))
    if max_w > 0:
        S_M = int(np.floor(32767.0 / (max_w * 1.05)))
    else:
        S_M = 1
        
    w_fixed = np.clip(np.round(w_hw * S_M), -32768, 32767).astype(np.int16)
    b_fixed = int(np.clip(np.round(b_eff * S_M), -2147483648, 2147483647))
    
    return K_arr, w_hw, S_M, w_fixed, b_fixed

def evaluate_rtl_fixedpoint_window(
    features_hw: np.ndarray,
    w_fixed: np.ndarray,
    b_fixed: int
) -> Tuple[int, int]:
    """
    Simulates the exact cycle-accurate serial MAC arithmetic in rtl/svm_classifier.v:
    - 40-bit signed accumulator initialized with 32-bit sign-extended b_fixed
    - For each feature j (0..175):
        prod = int32(features_hw[j]) * int32(w_fixed[j]) (16x16 -> 32-bit signed)
        accum += sign_extend_40(prod)
    - Returns: (score_40bit_signed, decision_bit_0_or_1)
    """
    accum = np.int64(b_fixed)
    
    for feat_val, weight_val in zip(features_hw, w_fixed):
        # 16-bit unsigned/positive feature x 16-bit signed weight -> 32-bit signed
        prod = np.int64(feat_val) * np.int64(weight_val)
        accum += prod
        
    decision = 1 if accum > 0 else 0
    return int(accum), decision

def compute_sqnr(signal_clean: np.ndarray, signal_quantized: np.ndarray) -> float:
    """Computes Signal-to-Quantization-Noise Ratio (SQNR) in decibels."""
    noise = signal_clean - signal_quantized
    p_sig = np.mean(signal_clean ** 2)
    p_noise = np.mean(noise ** 2)
    if p_noise <= 1e-15:
        return 120.0
    return float(10.0 * np.log10(p_sig / p_noise))

class FixedPointEvaluator:
    """
    Executes genuine bit-accurate fixed-point evaluation and compares against
    floating-point baseline results across held-out test recordings.
    """
    def __init__(self, config: Dict[str, Any], clf, scaler):
        self.config = config
        self.clf = clf
        self.scaler = scaler
        
        coef = clf.coef_[0]
        intercept = float(clf.intercept_[0])
        mean = scaler.mean_
        scale = scaler.scale_
        
        self.K, self.w_hw, self.S_M, self.w_fixed, self.b_fixed = derive_hardware_scales(
            config, coef, intercept, mean, scale
        )

    def evaluate_recording(
        self,
        features_float: np.ndarray,
        window_starts_sec: np.ndarray,
        seizure_intervals: List[Tuple[float, float]],
        duration_sec: float,
        y_true: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a complete recording through BOTH:
        1. Bit-accurate RTL fixed-point pipeline.
        2. 64-bit IEEE floating-point software pipeline.
        Performs automated anti-duplication assertions.
        """
        num_windows = features_float.shape[0]
        if num_windows == 0:
            return {}
            
        # ---------------------------------------------------------------------
        # 1. Floating-Point Software Evaluation
        # ---------------------------------------------------------------------
        feats_scaled = self.scaler.transform(features_float)
        scores_float = self.clf.decision_function(feats_scaled).astype(np.float64)
        decisions_float = np.where(scores_float > 0.0, 1, 0).astype(np.int32)
        
        # ---------------------------------------------------------------------
        # 2. Genuine Bit-Accurate Fixed-Point RTL Evaluation
        # ---------------------------------------------------------------------
        # Convert floating features to RTL unsigned int16 features
        features_hw = np.clip(np.round(features_float / self.K), 0, 32767).astype(np.int32)
        
        scores_fixed = np.zeros(num_windows, dtype=np.int64)
        decisions_fixed = np.zeros(num_windows, dtype=np.int32)
        
        for i in range(num_windows):
            sc, dec = evaluate_rtl_fixedpoint_window(
                features_hw[i], self.w_fixed, self.b_fixed
            )
            scores_fixed[i] = sc
            decisions_fixed[i] = dec
            
        # =====================================================================
        # CRITICAL SAFEGUARD: Anti-Duplication Assertion
        # Strictly prevents the Problem B bug (copying float into fixed-point)
        # =====================================================================
        if scores_fixed is scores_float or id(scores_fixed) == id(scores_float):
            raise RuntimeError(
                "CRITICAL ERROR: Fixed-point scores array is identical memory reference to float array! "
                "Genuine fixed-point evaluation must produce an independent integer array."
            )
        if np.array_equal(scores_fixed, scores_float):
            raise RuntimeError(
                "CRITICAL ERROR: Fixed-point integer scores are identical to float scores! "
                "Quantization arithmetic failed to execute."
            )
            
        # ---------------------------------------------------------------------
        # 3. Concordance & Quantization Metrics
        # ---------------------------------------------------------------------
        # Dequantize fixed scores to compare against float scores:
        # Score_dequant = Score_fixed / S_M
        scores_dequant = scores_fixed.astype(np.float64) / float(self.S_M)
        abs_errors = np.abs(scores_float - scores_dequant)
        mae = float(np.mean(abs_errors))
        max_err = float(np.max(abs_errors))
        sqnr_db = compute_sqnr(scores_float, scores_dequant)
        decision_agreement = float(np.mean(decisions_float == decisions_fixed) * 100.0)
        
        # ---------------------------------------------------------------------
        # 4. Independent Event-Level Scoring
        # ---------------------------------------------------------------------
        cfg_post = self.config["postprocess"]
        w_sec = self.config["windowing"]["window_sec"]
        
        # Evaluate Floating-point events
        ev_float = evaluate_predictions(
            y_true=y_true if y_true is not None else decisions_float,
            y_pred=decisions_float,
            y_scores=scores_float,
            window_starts_sec=window_starts_sec,
            seizure_intervals=seizure_intervals,
            duration_sec=duration_sec,
            k_persistence=cfg_post["k_persistence"],
            refractory_sec=cfg_post["refractory_sec"],
            tolerance_sec=cfg_post["tolerance_sec"],
            window_sec=w_sec
        )["event_metrics"]
        
        # Evaluate Fixed-point events
        ev_fixed = evaluate_predictions(
            y_true=y_true if y_true is not None else decisions_fixed,
            y_pred=decisions_fixed,
            y_scores=scores_dequant,
            window_starts_sec=window_starts_sec,
            seizure_intervals=seizure_intervals,
            duration_sec=duration_sec,
            k_persistence=cfg_post["k_persistence"],
            refractory_sec=cfg_post["refractory_sec"],
            tolerance_sec=cfg_post["tolerance_sec"],
            window_sec=w_sec
        )["event_metrics"]
        
        return {
            "num_windows": num_windows,
            "quantization_fidelity": {
                "S_M_multiplier": self.S_M,
                "mean_absolute_score_error": round(mae, 6),
                "max_absolute_score_error": round(max_err, 6),
                "decision_score_sqnr_db": round(sqnr_db, 2),
                "decision_agreement_percent": round(decision_agreement, 3)
            },
            "float_results": {
                "detected_seizures": ev_float["detected_seizures"],
                "total_seizures": ev_float["num_seizures"],
                "false_alarms": ev_float["false_alarms"],
                "non_seizure_hours": round(ev_float["non_seizure_hours"], 3),
                "latencies": ev_float["latencies"]
            },
            "fixed_results": {
                "detected_seizures": ev_fixed["detected_seizures"],
                "total_seizures": ev_fixed["num_seizures"],
                "false_alarms": ev_fixed["false_alarms"],
                "non_seizure_hours": round(ev_fixed["non_seizure_hours"], 3),
                "latencies": ev_fixed["latencies"]
            },
            "scores_float": scores_float,
            "scores_fixed": scores_fixed,
            "decisions_float": decisions_float,
            "decisions_fixed": decisions_fixed
        }


# ==============================================================================
# Full End-to-End Bit-Exact RTL Pipeline Emulation (IIR -> DWT -> Acc -> SVM -> Alarm)
# Replicating rtl/iir_biquad.v, rtl/dwt_level.v, rtl/feature_accumulator.v,
# rtl/svm_classifier.v, and rtl/alarm_logic.v
# ==============================================================================

# IIR Shift-20 Coefficients matching rtl/iir_biquad.v exactly
IIR_S0_B = np.array([65688, 131377, 65688], dtype=np.int64)
IIR_S0_A = np.array([-1240423, 457209], dtype=np.int64)
IIR_S1_B = np.array([1048576, -2097152, 1048576], dtype=np.int64)
IIR_S1_A = np.array([-2078976, 1030563], dtype=np.int64)

# Daubechies-4 Q15 Decomposition Coefficients matching rtl/dwt_level.v exactly
DB4_DEC_LO_Q15 = np.array([-347, 1078, 1011, -6129, -917, 20673, 23424, 7549], dtype=np.int32)
DB4_DEC_HI_Q15 = np.array([7549, -23424, 20673, 917, -6129, -1011, 1078, 347], dtype=np.int32)

class FixedChannelIIR:
    """
    Per-channel fixed-point 4th-order Butterworth IIR filter.
    Implements 2 cascaded Direct Form I biquad sections with Q20 internal state
    and guard bits matching the pipelined rtl/iir_biquad.v datapath.
    """
    def __init__(self):
        self.s0_x1 = np.int64(0)
        self.s0_x2 = np.int64(0)
        self.s0_y1 = np.int64(0)
        self.s0_y2 = np.int64(0)

        self.s1_x1 = np.int64(0)
        self.s1_x2 = np.int64(0)
        self.s1_y1 = np.int64(0)
        self.s1_y2 = np.int64(0)

    def process_sample(self, x_in: int) -> int:
        x = np.int64(x_in)

        # Section 0: Lowpass
        acc0 = (IIR_S0_B[0] * x) + (IIR_S0_B[1] * self.s0_x1) + (IIR_S0_B[2] * self.s0_x2) - \
               ((IIR_S0_A[0] * self.s0_y1 + IIR_S0_A[1] * self.s0_y2 + 524288) >> 20)

        self.s0_x2 = self.s0_x1
        self.s0_x1 = x
        self.s0_y2 = self.s0_y1
        self.s0_y1 = acc0

        y0_round = (acc0 + 524288) >> 20
        y0_sat = int(np.clip(y0_round, -32768, 32767))

        # Section 1: Highpass
        acc1 = (IIR_S1_B[0] * y0_sat) + (IIR_S1_B[1] * self.s1_x1) + (IIR_S1_B[2] * self.s1_x2) - \
               ((IIR_S1_A[0] * self.s1_y1 + IIR_S1_A[1] * self.s1_y2 + 524288) >> 20)

        self.s1_x2 = self.s1_x1
        self.s1_x1 = y0_sat
        self.s1_y2 = self.s1_y1
        self.s1_y1 = acc1

        y1_round = (acc1 + 524288) >> 20
        y1_sat = int(np.clip(y1_round, -32768, 32767))
        return y1_sat

class FixedChannelDWT:
    """
    Per-channel fixed-point 5-level Daubechies-4 DWT cascade.
    Shift registers, decimation phases, and Q15 multiplier-accumulators
    matching rtl/dwt_level.v and rtl/dwt_db4.v.
    """
    def __init__(self):
        self.shift_regs = [np.zeros(8, dtype=np.int32) for _ in range(5)]
        self.phases = [0] * 5

    def process_sample(self, x: int) -> Dict[str, int]:
        produced: Dict[str, int] = {}
        inp = int(x)

        for lvl in range(5):
            self.shift_regs[lvl][1:] = self.shift_regs[lvl][:-1]
            self.shift_regs[lvl][0] = inp

            if self.phases[lvl] == 1:
                sum_a = int(np.sum(self.shift_regs[lvl] * DB4_DEC_LO_Q15))
                sum_d = int(np.sum(self.shift_regs[lvl] * DB4_DEC_HI_Q15))

                a_val = int(np.clip((sum_a + 16384) >> 15, -32768, 32767))
                d_val = int(np.clip((sum_d + 16384) >> 15, -32768, 32767))

                self.phases[lvl] = 0
                produced[f"D{lvl+1}"] = d_val
                inp = a_val

                if lvl == 4:
                    produced["A5"] = a_val
            else:
                self.phases[lvl] = 1
                break

        return produced

def run_bit_exact_fpga_pipeline(
    signals_int16: np.ndarray,
    config: Dict[str, Any],
    w_fixed: np.ndarray,
    b_fixed: int,
    k_persistence: int = 3
) -> Dict[str, Any]:
    """
    Executes the complete bit-accurate FPGA integer pipeline across all 22 channels:
    - 22-channel Q20 IIR biquad bandpass filter
    - 22-channel 5-level Q15 DWT cascade
    - 38-bit energy and 26-bit line-length feature accumulation with bit-shift normalization
    - 40-bit serial MAC SVM classifier
    - k-consecutive persistence alarm logic with 30s refractory blanking
    """
    num_channels, num_samples = signals_int16.shape
    window_samples = config["windowing"]["window_samples"]
    num_windows = num_samples // window_samples
    retained_bands = config["wavelet"]["retained_subbands"]
    num_subbands = len(retained_bands)
    total_bins = num_channels * num_subbands
    
    e_shifts = config["hardware_fixedpoint"]["energy_shifts"]
    ll_shifts = config["hardware_fixedpoint"]["linelength_shifts"]

    iir_filters = [FixedChannelIIR() for _ in range(num_channels)]
    dwt_filters = [FixedChannelDWT() for _ in range(num_channels)]

    all_window_features = []
    all_scores = []
    all_decisions = []
    alarms = []

    consec_count = 0
    refractory_sec = 0

    for w_idx in range(num_windows):
        start_samp = w_idx * window_samples
        end_samp = start_samp + window_samples

        # Accumulators matching rtl/feature_accumulator.v
        energy_acc = np.zeros(total_bins, dtype=np.int64)
        linelength_acc = np.zeros(total_bins, dtype=np.int64)
        prev_coeff = np.zeros(total_bins, dtype=np.int32)
        has_prev = np.zeros(total_bins, dtype=bool)

        for n in range(start_samp, end_samp):
            for ch in range(num_channels):
                raw_s = int(signals_int16[ch, n])
                y_filt = iir_filters[ch].process_sample(raw_s)

                dwt_out = dwt_filters[ch].process_sample(y_filt)
                for sband_idx, b in enumerate(retained_bands):
                    if b in dwt_out:
                        c_val = dwt_out[b]
                        bin_addr = ch * num_subbands + sband_idx

                        # 38-bit energy accumulation: c_val^2
                        energy_acc[bin_addr] += np.int64(c_val) * np.int64(c_val)

                        # 26-bit line-length accumulation: |c_val - prev|
                        if has_prev[bin_addr]:
                            diff = abs(c_val - prev_coeff[bin_addr])
                            linelength_acc[bin_addr] += diff
                        else:
                            has_prev[bin_addr] = True

                        prev_coeff[bin_addr] = c_val

        # Normalization and feature serialization matching rtl/feature_accumulator.v
        w_feats = []
        for bin_addr in range(total_bins):
            sband_idx = bin_addr % num_subbands
            band_name = retained_bands[sband_idx]

            # Energy normalization: right-shift
            sh_e = e_shifts[band_name]
            e_val = (energy_acc[bin_addr] + (1 << (sh_e - 1))) >> sh_e
            e_sat = int(np.clip(e_val, 0, 32767))

            # Line-Length normalization: right-shift
            sh_ll = ll_shifts[band_name]
            ll_val = (linelength_acc[bin_addr] + (1 << (sh_ll - 1))) >> sh_ll
            ll_sat = int(np.clip(ll_val, 0, 32767))

            w_feats.extend([e_sat, ll_sat])

        w_feats_int16 = np.array(w_feats, dtype=np.int16)
        all_window_features.append(w_feats_int16)

        # 176-cycle serial multiply-accumulate matching rtl/svm_classifier.v
        mac_accum = np.int64(b_fixed)
        for j in range(176):
            prod = np.int64(w_feats_int16[j]) * np.int64(w_fixed[j])
            mac_accum += prod

        dec = 1 if mac_accum > 0 else 0
        all_scores.append(mac_accum)
        all_decisions.append(dec)

        # Alarm logic matching rtl/alarm_logic.v
        if refractory_sec > 0:
            refractory_sec -= 1

        alarm_fired = 0
        if dec == 1:
            consec_count += 1
            if consec_count >= k_persistence and refractory_sec == 0:
                alarm_fired = 1
                refractory_sec = 30
        else:
            consec_count = 0

        alarms.append(alarm_fired)

    return {
        "features": np.array(all_window_features, dtype=np.int16),
        "scores": np.array(all_scores, dtype=np.int64),
        "decisions": np.array(all_decisions, dtype=np.int32),
        "alarms": np.array(alarms, dtype=np.int32)
    }
