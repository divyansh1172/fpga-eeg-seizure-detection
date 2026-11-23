# PART 3: Real-Time Hardware Playback Demonstration (Stage 7)
**Lead Owners:** Member 1 (Host Streaming Harness) & Member 4 (Board Demo Lead)  
**Goal:** Connect the RealDigital Boolean Board over USB-UART at 230,400 baud, stream pre-recorded clinical EEG records from PC to FPGA, and demonstrate real-time seizure alarm assertion on board LEDs, RGB status indicators, and the 7-segment display.

---

## 1. Hardware Setup & Connection
1. Connect the RealDigital Boolean Board to your PC using a micro-USB cable.
2. Ensure the board power switch is turned ON.
3. Open Windows Device Manager (or `ls /dev/ttyUSB*` on Linux) and note the COM port assigned to the Silicon Labs CP2102N USB-UART bridge (e.g., `COM3`, `COM4`, or `/dev/ttyUSB0`).
4. Program the FPGA with `results/top_seizure_detector.bit` using Vivado Hardware Manager or the batch script:
   ```powershell
   vivado -mode batch -source "scripts/program_board.tcl"
   ```

---

## 2. UART Binary Streaming Protocol
To stream 22 channels at $f_s = 256\text{ Hz}$ ($5{,}632\text{ samples/s}$), each sample is framed into a compact 4-byte binary packet transmitted at 230,400 baud (23,040 bytes/s capacity; 22,528 bytes/s utilized $\approx 97.8\%$ link efficiency):

```
Byte 0: 0xAA (Packet Start Synchronization Header)
Byte 1: Channel Index [0 .. 21] (5 bits, 0 to 21)
Byte 2: Sample Data MSB (16-bit signed Q1.15 two's complement)
Byte 3: Sample Data LSB (16-bit signed Q1.15 two's complement)
```

The FPGA receiver `rtl/uart_rx.v` detects `0xAA`, extracts the channel ID and 16-bit signed sample, and routes it to the corresponding channel circular buffer in Block RAM.

---

## 3. Host Streaming Harness (`scripts/stream_eeg_uart.py`)
The Python streaming harness:
1. Opens the serial port at 230,400 baud, 8 data bits, no parity, 1 stop bit (8-N-1).
2. Loads a pre-extracted clinical EEG clip (e.g., `chb01_03.edf` spanning $t = 2950\text{ s}$ to $t = 3050\text{ s}$, which contains the onset at $t_{\text{onset}} = 2996\text{ s}$).
3. Paces transmission at exactly $256\text{ Hz}$ ($3.906\text{ ms}$ per 22-channel frame), simulating real-time continuous electrode acquisition.
4. Monitors board response bytes (alarm triggers, window score telemetry) and logs latency with sub-millisecond precision.

### Running the Streaming Demo:
```powershell
# From project root:
python scripts/stream_eeg_uart.py --port COM3 --baud 230400 --clip chb01_03
```

---

## 4. Physical Board Indicators During Demonstration

| Operational State | Slide Switches | Board Peripheral | Observed Physical Behavior |
|---|---|---|---|
| **Power On / Reset** | `SW[1:0] = 10` ($k=3$) | Pushbutton `BTN0` | Press `BTN0` to reset. 7-segment shows `INIT 00`. |
| **Normal Streaming** | `SW[1:0] = 10` ($k=3$) | RGB LED 0 | Solid **GREEN**. |
| **Normal Streaming** | `SW[1:0] = 10` ($k=3$) | 7-Segment Display | Digits 7..4 show elapsed playback time (e.g., `2990`), Digits 3..0 show `IDLE`. |
| **Early Ictal Build-up** | `SW[1:0] = 10` ($k=3$) | Discrete LEDs `LD[2:0]` | LEDs light sequentially as consecutive positive windows accumulate ($k=1, 2$). |
| **Seizure Alarm Asserted** | `SW[1:0] = 10` ($k=3$) | Discrete LED `LD15` | **STROBES RAPIDLY** (Pin `A4`). |
| **Seizure Alarm Asserted** | `SW[1:0] = 10` ($k=3$) | RGB LED 0 | Latches into flashing **RED**. |
| **Seizure Alarm Asserted** | `SW[1:0] = 10` ($k=3$) | 7-Segment Display | Digits 7..4 display `SEIZ`, Digits 3..0 display latency (e.g., `0008` for $\tau = 8.0\text{ s}$). |
| **Refractory Suppression** | `SW[1:0] = 10` ($k=3$) | Alarm FSM | Further alarms suppressed for 30 seconds; state auto-clears back to Green. |

---

## 5. Latency Verification & Filter Group Delay Characterization
During the live demo, record the exact timestamps:
- $t_{\text{onset}}$: Clinical seizure onset annotation ($2996.0\text{ s}$ for `chb01_03`).
- $t_{\text{alarm,sw}}$: Software detection timestamp ($3004.0\text{ s} \implies \tau_{\text{sw}} = 8.0\text{ s}$).
- $t_{\text{alarm,hw}}$: Physical FPGA alarm strobe on `LD15`.
- Compare software vs. hardware timestamps: the hardware datapath incurs an additional causal filter group delay:
  $$d_{\text{DWT}} \approx 0.20\text{--}0.25\text{ s}$$
  Confirm that $t_{\text{alarm,hw}} = t_{\text{alarm,sw}} + d_{\text{DWT}}$, providing physical experimental validation of the causal filter math presented in Section 5.2 of the report!

---

## 6. Viva Demonstration Video & Photograph Guidelines
Per the course flier: "The team must present their work on the Boolean Board, and answer questions."
To ensure an airtight grade:
1. **Photographs for Report:** Take clear photos of the Boolean Board:
   - Photo 1: Normal streaming (Green RGB LED, 7-segment showing playback time).
   - Photo 2: Active Seizure Alarm (Red RGB LED, `LD15` illuminated, 7-segment showing `SEIZ 0008`).
2. **Demo Video Clip:** Record a short 2-minute video showing the PC terminal streaming EEG samples and the board LED flashing Red at the exact moment of seizure onset.
3. Keep the video and board photos in `results/demo/` for embedding into the final report and viva slide deck.

---

## 7. Turnkey Execution Prompt for Part 3

```markdown
### PROMPT TO EXECUTE PART 3:
You are the board demonstration specialist for EE2000 Team 15.
Please set up and verify the real-time hardware playback demonstration:
1. Develop `scripts/stream_eeg_uart.py` to stream pre-extracted 22-channel EEG clips over USB-UART at 230,400 baud.
2. Test playback of clinical seizure clip `chb01_03.edf` (onset at 2996 s) and a non-seizure control clip.
3. Verify that:
   - Normal streaming shows solid Green on RGB0 and increments the 7-segment window count.
   - At t = 3004 s (k = 3), LED15 strobes, RGB0 turns Red, and 7-segment displays `SEIZ 0008`.
   - 30-second refractory blanking prevents duplicate false triggers.
4. Measure and log the hardware latency and causal filter delay (d_DWT ≈ 0.25 s).
5. Save the terminal playback log to `results/uart_demo_playback.log` and document the results in `process.md`.
```
