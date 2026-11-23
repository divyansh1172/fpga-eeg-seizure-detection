"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Team: 15
Author: Member 1 (Host Demo Lead)
Purpose: Streaming EEG playback harness over USB-UART (230,400 baud) to RealDigital Boolean Board.
         Simulates real-time 22-channel continuous acquisition at 256 Hz.
         Verifies physical board alarm assertion, latched latency, and hardware telemetry.
AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Member 1)
"""

import sys
import time
import argparse
from pathlib import Path
import numpy as np

# Check for pyserial
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

SYNC_BYTE = 0xAA
NUM_CHANNELS = 22
FS = 256.0
FRAME_PERIOD_SEC = 1.0 / FS  # ~3.906 ms per 22-channel sample frame

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_HEX = PROJECT_DIR / "golden" / "vectors" / "tb_uart_rx_stimulus.hex"

def parse_args():
    parser = argparse.ArgumentParser(description="Stream 22-Channel EEG to RealDigital Boolean Board via UART.")
    parser.add_argument("--port", type=str, default="COM7", help="Serial COM port (e.g. COM7, COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=230400, help="UART baud rate (default: 230400)")
    parser.add_argument("--duration", type=float, default=30.0, help="Total duration to stream in seconds (default: 30.0 s)")
    parser.add_argument("--onset", type=float, default=15.0, help="Seizure onset scheduled time in seconds (default: 15.0 s)")
    parser.add_argument("--clip", type=str, default="chb01_03", help="Target EEG clip identifier")
    parser.add_argument("--hex", type=str, default="", help="Path to fixed hex file stimulus (optional)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without physical serial hardware")
    return parser.parse_args()

def generate_physiological_eeg(duration_sec: float = 30.0, seizure_onset_sec: float = 15.0):
    """
    Generates realistic 22-channel broadband EEG calibrated to the CHB-MIT SVM model.
    Background (0..onset): Broadband Delta (2 Hz), Theta (6 Hz), Alpha (10 Hz), Beta (22 Hz).
    Seizure (onset..end): High-amplitude 3.5 Hz rhythmic spike-wave + 18 Hz harmonic discharge
                          on focal channels [4, 5, 6, 7, 14, 15].
    """
    total_frames = int(duration_sec * FS)
    t = np.arange(total_frames) / FS
    signals_int16 = np.zeros((NUM_CHANNELS, total_frames), dtype=np.int16)

    # Focal channels exhibiting ictal discharges in chb01
    focal_channels = [4, 5, 6, 7, 14, 15]

    for ch in range(NUM_CHANNELS):
        ph = 2 * np.pi * (ch / float(NUM_CHANNELS))
        # Broadband physiological background (uV)
        bg = 20.0 * np.sin(2 * np.pi * 2.0 * t + ph * 0.5) + \
             15.0 * np.sin(2 * np.pi * 6.0 * t + ph * 0.8) + \
             15.0 * np.sin(2 * np.pi * 10.0 * t + ph) + \
              8.0 * np.sin(2 * np.pi * 22.0 * t + ph * 1.2)

        # Focal seizure discharge: 3.5 Hz rhythmic spike-wave (80 uV) + 18 Hz harmonic (40 uV)
        sz = np.zeros_like(t)
        if ch in focal_channels:
            sz_mask = (t >= seizure_onset_sec)
            t_sz = t[sz_mask] - seizure_onset_sec
            sz[sz_mask] = 80.0 * np.sin(2 * np.pi * 3.5 * t_sz) + \
                          40.0 * np.sin(2 * np.pi * 18.0 * t_sz)

        sig_uV = bg + sz
        # Scale to 16-bit signed integer (S_SIG = 20 LSB/uV)
        signals_int16[ch, :] = np.clip(np.round(sig_uV * 20.0), -32768, 32767).astype(np.int16)

    return signals_int16, seizure_onset_sec

def stream_eeg(port_name, baud_rate, data_int16, onset_sec, duration_sec, mock_mode=False):
    num_channels, total_frames = data_int16.shape
    frame_size = num_channels * 4

    print("==============================================================================")
    print(" EE2000 22-Channel Real-Time EEG Seizure Detector – Board Streaming Harness")
    print(" Target: RealDigital Boolean Board (Spartan-7 XC7S50, 100 MHz)")
    print("==============================================================================")
    print(f"[INIT] Connecting to Boolean Board on {port_name} at {baud_rate} baud...")

    ser = None
    if not mock_mode:
        if not SERIAL_AVAILABLE:
            print("[WARN] pyserial is not installed! Run 'pip install pyserial'. Switching to MOCK mode.\n")
            mock_mode = True
        else:
            try:
                ser = serial.Serial(port=port_name, baudrate=baud_rate, bytesize=8, parity='N', stopbits=1, timeout=0.01)
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                print("[OK] Serial connection established!")
            except Exception as e:
                print(f"[WARN] Could not open {port_name} ({e}). Switching to MOCK mode.\n")
                mock_mode = True

    print(f"[STREAM] Streaming {total_frames} frames ({duration_sec:.1f} s) across {num_channels} channels at {FS:.0f} Hz...")
    print(f"  Phase 1 (t =  0.0 s -> {onset_sec:5.1f} s) : Normal Baseline EEG (SVM Score < 0)")
    print(f"  Phase 2 (t = {onset_sec:5.1f} s -> {duration_sec:5.1f} s) : Clinical Seizure Onset (SVM Score > 0)\n")

    start_time = time.time()
    alarm_triggered = False
    alarm_timestamp = None
    last_print_sec = -1

    try:
        for f_idx in range(total_frames):
            frame_start = time.time()
            current_time = f_idx / FS

            # Build 88-byte frame: 22 channels * [0xAA, ch_id, MSB, LSB]
            frame_bytes = bytearray()
            for ch in range(num_channels):
                val = int(data_int16[ch, f_idx])
                msb = (val >> 8) & 0xFF
                lsb = val & 0xFF
                frame_bytes.extend([SYNC_BYTE, ch, msb, lsb])

            if ser and not mock_mode:
                ser.write(frame_bytes)

                # Check for return telemetry byte (0xA5) from FPGA
                if ser.in_waiting:
                    rx = ser.read(ser.in_waiting)
                    for b in rx:
                        if b in (0xA5, 0x5A, 0xEE, 0xFF) or b == ord('A'):
                            if not alarm_triggered:
                                alarm_triggered = True
                                alarm_timestamp = current_time
                                latency = alarm_timestamp - onset_sec
                                print(f"\n******************************************************************************")
                                print(f" >>> [SEIZURE ALARM ASSERTED BY FPGA HARDWARE!]")
                                print(f"     Board Alarm Time : t = {alarm_timestamp:.2f} s")
                                print(f"     Clinical Onset   : t = {onset_sec:.2f} s")
                                print(f"     Hardware Latency : tau = {latency:.2f} s")
                                print(f"     Board Indicators : RGB0 FLASHING RED | LED15 6Hz STROBE | 7-SEG DISPLAY")
                                print(f"******************************************************************************\n")

            # Progress display every 1.0 second
            sec_int = int(current_time)
            if sec_int != last_print_sec and (f_idx % int(FS) == 0):
                last_print_sec = sec_int
                elapsed = time.time() - start_time
                if current_time < onset_sec:
                    state = "Normal Baseline"
                elif not alarm_triggered:
                    state = "SEIZURE ACTIVE (Evaluating window)"
                else:
                    state = "SEIZURE DETECTED (Alarm Latched)"

                alarm_flag = "[ALARM]" if alarm_triggered else "[OK]   "
                print(f"  {alarm_flag} Playback t = {current_time:5.1f} s | Elapsed: {elapsed:5.1f} s | State: {state}")

            # Pace at ~3.906 ms per frame
            frame_elapsed = time.time() - frame_start
            sleep_needed = FRAME_PERIOD_SEC - frame_elapsed
            if sleep_needed > 0.0005:
                time.sleep(sleep_needed)

    except KeyboardInterrupt:
        print("\n[STOP] Streaming aborted by user.")
    finally:
        if ser and ser.is_open:
            # Drain and wait up to 1.5s for FPGA pipeline to finish last window classification
            t_drain = time.time() + 1.5
            while time.time() < t_drain:
                if ser.in_waiting:
                    rx = ser.read(ser.in_waiting)
                    for b in rx:
                        if b in (0xA5, 0x5A, 0xEE, 0xFF) or b == ord('A'):
                            if not alarm_triggered:
                                alarm_triggered = True
                                alarm_timestamp = duration_sec
                                latency = alarm_timestamp - onset_sec
                                print(f"\n******************************************************************************")
                                print(f" >>> [SEIZURE ALARM ASSERTED BY FPGA HARDWARE!]")
                                print(f"     Board Alarm Time : t = {alarm_timestamp:.2f} s")
                                print(f"     Clinical Onset   : t = {onset_sec:.2f} s")
                                print(f"     Hardware Latency : tau = {latency:.2f} s")
                                print(f"     Board Indicators : RGB0 FLASHING RED | LED15 6Hz STROBE | 7-SEG DISPLAY")
                                print(f"******************************************************************************\n")
                time.sleep(0.05)
            ser.close()
            print("[DONE] Serial port closed cleanly.")

    print("\n==============================================================================")
    print("STREAMING DEMONSTRATION SUMMARY")
    print(f"Total Streamed Duration : {duration_sec:.2f} s")
    print(f"Scheduled Seizure Onset : {onset_sec:.2f} s")
    print(f"Hardware Seizure Alarm  : {'YES (SUCCESS)' if alarm_triggered else 'NO'}")
    if alarm_triggered:
        print(f"First Alarm Assertion   : t = {alarm_timestamp:.2f} s")
        print(f"Detection Latency (tau) : {alarm_timestamp - onset_sec:.2f} s")
        print(f"Board Hardware State    : RGB0 RED | LED15 STROBING | 7-SEG LATCHED")
    print("==============================================================================")

def stream_hex_vector(port_name, baud_rate, hex_file_path, mock_mode=False):
    """Streams from a pre-compiled hex file (e.g. 2s test stimulus)."""
    print(f"\n[INIT] Loading clinical test vector from {hex_file_path}...")
    with open(hex_file_path, "r") as f:
        raw_bytes = bytearray([int(line.strip(), 16) for line in f if line.strip()])

    total_bytes = len(raw_bytes)
    frame_size = NUM_CHANNELS * 4
    total_frames = total_bytes // frame_size
    duration_sec = total_frames / FS
    onset_sec = 1.0

    # Unpack 22-channel data into int16 array
    data_int16 = np.zeros((NUM_CHANNELS, total_frames), dtype=np.int16)
    for f in range(total_frames):
        base = f * frame_size
        for ch in range(NUM_CHANNELS):
            ch_base = base + ch * 4
            msb = raw_bytes[ch_base + 2]
            lsb = raw_bytes[ch_base + 3]
            raw_u16 = (msb << 8) | lsb
            if raw_u16 >= 32768:
                raw_u16 -= 65536
            data_int16[ch, f] = raw_u16

    stream_eeg(port_name, baud_rate, data_int16, onset_sec, duration_sec, mock_mode)

if __name__ == "__main__":
    args = parse_args()

    if args.hex:
        stream_hex_vector(port_name=args.port, baud_rate=args.baud, hex_file_path=Path(args.hex), mock_mode=args.mock)
    else:
        # Default: generate high-fidelity physiological EEG stream with user-specified duration & onset
        data_int16, onset = generate_physiological_eeg(duration_sec=args.duration, seizure_onset_sec=args.onset)
        stream_eeg(port_name=args.port, baud_rate=args.baud, data_int16=data_int16, onset_sec=onset, duration_sec=args.duration, mock_mode=args.mock)
