# RealDigital Boolean Board (AMD Spartan-7 XC7S50)
## Complete Step-by-Step FPGA Implementation & Live Demo Tutorial
**EE2000 Project Team 15 — Real-Time Multichannel EEG Seizure Detection**

---

## 1. Prerequisites & Equipment Checklist

### Hardware:
1. **RealDigital Boolean Board** (AMD Spartan-7 `xc7s50csga324-1`).
2. **Micro-USB to USB-A/C Cable** with data lines (verify it is not a power-only charging cable).
3. **Host Computer** (Windows, Linux, or macOS) with Vivado 2020.2 or later installed.
4. **CP2102N USB-to-UART Bridge Driver** (standard Silicon Labs VCP driver; usually auto-detected on modern OS).

### Software & Repository Files:
* **Synthesis Script:** `scripts/run_vivado_synth.tcl` (One-command non-project synthesis & bitstream generation)
* **Physical Constraints:** `rtl/boolean_board.xdc` (RealDigital Boolean Board master pinout for Spartan-7 XC7S50)
* **Trained Model Weights:** `weights.mem` and `rtl/weights.mem` (176 hex words of folded linear SVM weights loaded via `$readmemh`)
* **Verilog RTL Sources (10 files):**
  1. `rtl/top_seizure_detector.v` (Top-level integration & board I/O)
  2. `rtl/uart_rx.v` (230,400-baud UART receiver with framing error check)
  3. `rtl/uart_tx.v` (230,400-baud UART telemetry transmitter for `0xA5` alert byte)
  4. `rtl/iir_biquad.v` (22-channel time-multiplexed 4th-order Butterworth bandpass filter)
  5. `rtl/dwt_level.v` (Modular 2-stage pipelined 8-tap db4 FIR with per-channel state RAM)
  6. `rtl/dwt_db4.v` (5-level dyadic DWT cascade emitting D3, D4, D5, A5 subbands)
  7. `rtl/feature_accumulator.v` (Double-buffered ping-pong Energy & Line-Length extractor)
  8. `rtl/svm_classifier.v` (176-cycle serial MAC with 40-bit accumulator & 32-bit bias)
  9. `rtl/alarm_logic.v` (Persistence $k \in \{1, 2, 3, 5\}$, 30 s refractory blanking, latency latch)
  10. `rtl/seven_seg_controller.v` (8-digit multiplexed common-anode 7-segment display driver)
* **Host Python Streaming Script:** `scripts/stream_eeg_uart.py` (Streams 22-channel EEG frames and listens for `0xA5` alert)
* **Evaluation Records / Test Stimulus:** `golden/vectors/tb_uart_rx_stimulus.hex` or synthetic EEG generator in `scripts/stream_eeg_uart.py`.

---

## 2. Hardware Setup & Controls Configuration

1. **Inspect Board Power Jumpers:**
   * Locate the power select jumper near the micro-USB connector. Set it to **USB power** (5V).
2. **Connect to Host PC:**
   * Plug the micro-USB cable into the **PROG / UART** port on the Boolean Board and connect to your PC.
   * Slide the board power switch to **ON**. The red power LED will illuminate.
3. **Board Controls (Buttons & Switches):**
   * **BTN0 (Pin J2 - `rst`):** Master System Reset (Active-High). Press momentarily to reset the entire FPGA pipeline.
   * **BTN1 (Pin J5 - `btn[1]`):** Manual Alarm Clear. Press to dismiss a latched seizure alarm and return to normal monitoring.
   * **SW[1:0] (Pins U2, V2 - `sw[1:0]`):** Persistence Filter Threshold ($k$):
     * `SW[1:0] = 00` $\rightarrow k=1$ (Immediate trigger on 1 positive window)
     * `SW[1:0] = 01` $\rightarrow k=2$ (Trigger on 2 consecutive positive windows)
     * `SW[1:0] = 10` $\rightarrow k=3$ (**Default recommended baseline**)
     * `SW[1:0] = 11` $\rightarrow k=5$ (High specificity / low false alarm mode)
   * **SW[15:2]:** Set to **DOWN (0)** for normal operation.

---

## 3. Step 1: Generate the FPGA Bitstream

You can generate the bitstream using either the automated non-project Tcl flow or the Vivado GUI.

### Method A: Automated Batch Command (Recommended & Fast)
Open your terminal (or Vivado Tcl Shell / Command Prompt) in the repository root directory:

```bash
# On Windows / Linux / macOS (adjust path to vivado executable if needed):
vivado -mode batch -source scripts/run_vivado_synth.tcl
```

* This automated script:
  1. Sets the target part to `xc7s50csga324-1`.
  2. Reads all synthesizable RTL files in `rtl/` (excluding simulation testbenches).
  3. Reads `rtl/boolean_board.xdc`.
  4. Runs synthesis, logic optimization, placement, physical optimization, and routing.
  5. Verifies 100 MHz timing closure ($WNS > 0$, $WHS > 0$).
  6. Generates `vivado_build/top_seizure_detector.bit` and timing/utilization reports.

---

### Method B: Vivado GUI Flow

1. Open **Vivado**.
2. Select **Create Project** $\rightarrow$ Project Name: `eeg_seizure_boolean` $\rightarrow$ Project Type: **RTL Project**.
3. **Add Sources:**
   * Click **Add Files** and select all `.v` files from `rtl/` **except** files starting with `tb_*.v`.
   * Set Top Module to `top_seizure_detector`.
4. **Add Constraints:**
   * Add `rtl/boolean_board.xdc`.
5. **Select Target Part:**
   * Family: `Spartan-7`
   * Package: `csga324`
   * Speed: `-1`
   * Select Part: `xc7s50csga324-1` (or search "Boolean" if board files are installed).
6. **Generate Bitstream:**
   * In the Flow Navigator (left sidebar), click **Generate Bitstream**.
   * Vivado will prompt to run Synthesis and Implementation first. Click **Yes**.
   * Wait for completion (typically 3–5 minutes).

---

## 4. Step 2: Program the Bitstream to the Boolean Board

1. In Vivado, click **Open Hardware Manager** $\rightarrow$ **Open Target** $\rightarrow$ **Auto Connect**.
2. Under the Hardware window, you should see:
   * `localhost(1)` $\rightarrow$ `xilinx_tcf/...` $\rightarrow$ `xc7s50_0`
3. Right-click on `xc7s50_0` and select **Program Device...**.
4. In the dialog box:
   * **Bitstream file:** Browse to `vivado_build/top_seizure_detector.bit` (or `<project_name>.runs/impl_1/top_seizure_detector.bit`).
5. Click **Program**.
6. **Confirmation on Board:**
   * The green **DONE** LED on the Boolean Board will turn **ON**.
   * `LED[0]` will begin blinking as a 1 Hz heartbeat indicator.
   * The 8-digit 7-segment display will illuminate showing initial playback status.
   * The RGB LEDs will show **Solid Green** (System Ready / Non-seizure baseline).

---

## 5. Step 3: Stream Live EEG from Host PC via UART

The host streaming script transmits 22-channel Q1.15 digitized EEG samples over the USB-UART bridge at 230,400 baud.

### Identify the COM Port / Device Node:
* **Windows:** Open Device Manager $\rightarrow$ Ports (COM & LPT) $\rightarrow$ Note `COMx` (e.g. `COM3` or `COM4`).
* **Linux:** Check `ls /dev/ttyUSB*` (typically `/dev/ttyUSB1`).
* **macOS:** Check `ls /dev/cu.usbserial-*` or `/dev/cu.SLAB_USBtoUART*`.

### Execute the Real-Time Playback:
From your host terminal, run:

```bash
# Example for Windows:
python scripts/stream_eeg_uart.py --port COM3 --baud 230400 --record chb01_03.edf

# Example for Linux:
python scripts/stream_eeg_uart.py --port /dev/ttyUSB1 --baud 230400 --record chb01_03.edf

# Example for macOS:
python scripts/stream_eeg_uart.py --port /dev/cu.usbserial-0001 --baud 230400 --record chb01_03.edf
```

---

## 6. Step 4: Live Board Telemetry & What to Observe

During the demo, explain the board indicators to the examiners as the streaming progresses:

| Peripheral | Normal (Inter-Ictal Baseline) | Seizure Onset Detected (Ictal State) |
|---|---|---|
| **LED[0]** | Blinks at 1 Hz (FPGA clock / system heartbeat). | Blinks at 1 Hz. |
| **LED[14..1]** | Channel activity telemetry monitor. | Flashes dynamically reflecting high-energy sub-bands. |
| **LED[15]** | **OFF** | **Active Strobe / Flashing Alarm** ($k=3$ consecutive positive windows). |
| **RGB0 / RGB1** | **Solid Green** (Status Normal). | **Latched Solid Red** (Seizure Alarm Asserted). |
| **7-Segment Display** | Shows current playback time frame ($t$ in seconds). | Latches **`SEIZ 01`** and displays measured latency $\tau$ (e.g. `08.0s`). |

---

## 7. Recommended Demo Flow for Viva Evaluation

1. **Step 1: Baseline / Control Test (Demonstrating Zero False Alarms):**
   * Run control recording:
     ```bash
     python scripts/stream_eeg_uart.py --port <PORT> --baud 230400 --record chb01_01.edf
     ```
   * *Show examiners:* RGB LED stays **Green**, `LED[15]` stays **OFF**, zero false alarms raised.

2. **Step 2: Live Seizure Onset Detection:**
   * Run seizure recording:
     ```bash
     python scripts/stream_eeg_uart.py --port <PORT> --baud 230400 --record chb01_03.edf
     ```
   * *Point to the time counter on the 7-segment display.*
   * At $t = 3004$\,s (8.0 s after clinical onset at 2996 s), observe:
     * `LED[15]` instantly strobes.
     * RGB LEDs switch from Green to **Red**.
     * 7-segment display freezes on alarm and shows latency.
     * Host terminal prints: `[ALARM ASSERTED] Hardware matched software gold model!`

3. **Step 3: Reset & Blanking Test:**
   * Toggle `SW0` UP then DOWN to clear the alarm state, or allow the internal 30\,s refractory blanking timer to re-arm automatically.

---

## 8. Common Troubleshooting & FAQs

* **Q: Vivado says "No hardware target found"?**
  * *Fix:* Ensure the board is powered on, micro-USB cable is connected to the PROG port, and the Silicon Labs CP2102N driver is installed.
* **Q: Python says `SerialException: could not open port`?**
  * *Fix:* Ensure Vivado's serial terminal or any other serial monitor (PuTTY, Arduino IDE) is disconnected and not locking the COM port.
* **Q: `LED[15]` does not trigger?**
  * *Fix:* Check `SW0` (Reset switch). It must be **DOWN (0)**. If `SW0` is UP (1), the pipeline is held in reset.
* **Q: Timing Slack negative after modifying RTL?**
  * *Fix:* Always maintain the 2-cycle pipeline registers in `svm_classifier.v` and ensure DSP48E1 dynamic wire-shifting is preserved.
