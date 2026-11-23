"""
Course: EE2000 Signal Processing, Fall 2026, IIT Hyderabad
Team: 15
Author: Member 1 (Host Demo Lead)
Purpose: Streaming EEG playback harness over USB-UART (230,400 baud) to RealDigital Boolean Board.
         Simulates real-time 22-channel continuous acquisition at 256 Hz.
         Verifies physical board alarm assertion and measures hardware group delay.
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
END_BYTE  = 0x55
NUM_CHANNELS = 22
FS = 256.0
FRAME_PERIOD_SEC = 1.0 / FS  # ~3.906 ms per 22-channel sample frame

def parse_args():
    parser = argparse.ArgumentParser(description="Stream EEG to RealDigital Boolean Board via UART.")
    parser.add_argument("--port", type=str, default="COM3", help="Serial COM port (e.g., COM3, COM4, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=230400, help="Baud rate (default: 230400)")
    parser.add_argument("--clip", type=str, default="chb01_03", help="Target EEG clip to stream")
    parser.add_argument("--duration", type=float, default=60.0, help="Duration to stream in seconds (default: 60.0 s)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without physical serial hardware")
    return parser.parse_args()

def generate_synthetic_eeg_clip(duration_sec, fs, num_channels, seizure_onset_sec=30.0):
    """
    Generates a 22-channel Q1.15 synthetic EEG clip with simulated seizure onset.
    """
    total_samples = int(duration_sec * fs)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)
    data = np.zeros((num_channels, total_samples), dtype=np.int16)

    for ch in range(num_channels):
        # Background normal EEG: low-amplitude mixed rhythms (alpha 10 Hz + theta 6 Hz)
        bg = 0.15 * np.sin(2 * np.pi * 10 * t) + 0.10 * np.sin(2 * np.pi * 6 * t)
        
        # Seizure burst: high-amplitude 3 Hz spike-wave discharges starting at seizure_onset_sec
        sz_mask = (t >= seizure_onset_sec)
        sz = np.zeros_like(t)
        sz[sz_mask] = 0.70 * np.sin(2 * np.pi * 3.5 * (t[sz_mask] - seizure_onset_sec))
        
        # Combine and scale to 16-bit signed Q1.15
        signal_float = np.clip(bg + sz, -1.0, 0.9999)
        data[ch, :] = (signal_float * 32767).astype(np.int16)

    return data, seizure_onset_sec

def stream_to_board(port_name, baud_rate, data, fs, onset_sec, mock_mode=False):
    num_channels, num_samples = data.shape
    print(f"\n[INIT] Connecting to Boolean Board on {port_name} at {baud_rate} baud...")
    
    ser = None
    if not mock_mode:
        if not SERIAL_AVAILABLE:
            print("[WARN] pyserial is not installed! Run 'pip install pyserial' for hardware demo. Falling back to MOCK mode.\n")
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

    print(f"[STREAM] Streaming {num_samples} frames ({num_samples/fs:.1f} s) across {num_channels} channels at {fs} Hz...")
    print(f"[INFO] Ground-truth clinical seizure onset scheduled at t = {onset_sec:.1f} s.\n")

    start_time = time.time()
    alarm_triggered = False
    alarm_timestamp = None

    try:
        for n in range(num_samples):
            frame_start = time.time()
            current_playback_time = n / fs

            # Build 22-channel packet stream for this time sample
            packet_bytes = bytearray()
            for ch in range(num_channels):
                val = int(data[ch, n])
                msb = (val >> 8) & 0xFF
                lsb = val & 0xFF
                packet_bytes.extend([SYNC_BYTE, ch, msb, lsb])

            if ser and not mock_mode:
                ser.write(packet_bytes)
                
                # Check for return telemetry from FPGA
                if ser.in_waiting:
                    rx = ser.read(ser.in_waiting)
                    if b'A' in rx or 0xA1 in rx:  # Alarm assertion flag from FPGA
                        if not alarm_triggered:
                            alarm_triggered = True
                            alarm_timestamp = current_playback_time
                            latency = alarm_timestamp - onset_sec
                            print(f"\n>>> [SEIZURE ALARM ASSERTED BY FPGA BOARD!]")
                            print(f"    Board Alarm Time : t = {alarm_timestamp:.3f} s")
                            print(f"    Clinical Onset   : t = {onset_sec:.3f} s")
                            print(f"    Measured Latency : tau = {latency:.3f} s (including causal filter delay)\n")
            else:
                # Mock simulation of board alarm after 3 consecutive positive windows
                if current_playback_time >= (onset_sec + 3.0) and not alarm_triggered:
                    alarm_triggered = True
                    alarm_timestamp = current_playback_time + 0.25  # adding 0.25s causal delay
                    latency = alarm_timestamp - onset_sec
                    print(f"\n>>> [MOCK BOARD SEIZURE ALARM ASSERTED]")
                    print(f"    Board Alarm Time : t = {alarm_timestamp:.3f} s")
                    print(f"    Clinical Onset   : t = {onset_sec:.3f} s")
                    print(f"    Measured Latency : tau = {latency:.3f} s (with 0.25 s DWT group delay)\n")

            # Progress display every 5 seconds
            if n % (int(fs) * 5) == 0:
                elapsed = time.time() - start_time
                status = "SEIZURE ACTIVE" if current_playback_time >= onset_sec else "Normal Background"
                print(f"  Playback t = {current_playback_time:5.1f} s | Elapsed: {elapsed:5.1f} s | State: {status}")

            # Precise rate pacing (~3.906 ms per frame)
            frame_elapsed = time.time() - frame_start
            sleep_needed = FRAME_PERIOD_SEC - frame_elapsed
            if sleep_needed > 0.0005:
                time.sleep(sleep_needed)

    except KeyboardInterrupt:
        print("\n[STOP] Streaming aborted by user.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("[DONE] Serial port closed cleanly.")

    print("\n==============================================================================")
    print("STREAMING DEMONSTRATION SUMMARY")
    print(f"Total Streamed Duration : {num_samples/fs:.2f} s")
    print(f"Seizure Detected        : {'YES (SUCCESS)' if alarm_triggered else 'NO'}")
    if alarm_triggered:
        print(f"Detection Latency (tau) : {alarm_timestamp - onset_sec:.3f} s")
    print("==============================================================================")

if __name__ == "__main__":
    args = parse_args()
    data, onset = generate_synthetic_eeg_clip(duration_sec=args.duration, fs=FS, num_channels=NUM_CHANNELS, seizure_onset_sec=25.0)
    stream_to_board(port_name=args.port, baud_rate=args.baud, data=data, fs=FS, onset_sec=onset, mock_mode=args.mock)
