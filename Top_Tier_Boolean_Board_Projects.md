# Top-Tier EE2000 Signal Processing Projects
**Target:** Xilinx Boolean Board (Spartan-7)
**Prerequisites:** Strong Verilog skills, willingness to purchase external Pmod hardware.
**Goal:** Absolute best grade, undeniable "wow" factor during the viva.

If you want the top grade in the class, your project must do three things:
1. **Solve a complex, mathematically rigorous Signal Processing (SP) problem.**
2. **Push the FPGA to its limits** (utilizing DSP slices, BRAM, and parallel architectures).
3. **Have a highly interactive, real-time physical demonstration.**

Here are 7 elite project ideas that meet all these criteria.

---

## 1. Acoustic Source Localization (Microphone Array Beamforming)
**The Concept:** You arrange 3 or 4 microphones in a line. When you snap your fingers or speak, the FPGA calculates exactly what angle the sound came from and lights up LEDs pointing in that direction.
*   **Signal Processing:** Delay-and-sum beamforming, Time Difference of Arrival (TDOA), Cross-Correlation, and interpolation.
*   **FPGA Challenge:** You must synchronize 4 SPI microphones perfectly, buffer the audio into BRAM, and run multiple cross-correlation engines in parallel using DSP slices to find the peak time delay.
*   **The Demo:** Highly interactive. The professor walks around the board, speaks, and the LEDs track their movement in real-time.
*   **Hardware to Buy:** 3x or 4x Digilent Pmod MIC3.

## 2. Real-Time Audio Noise Cancellation (LMS Adaptive Filter)
**The Concept:** The system listens to a noisy environment and a speech signal, and mathematically subtracts the noise in real-time. This is the foundation of AirPods Pro active noise cancellation.
*   **Signal Processing:** Stochastic gradient descent, adaptive FIR filters, Least Mean Squares (LMS) weight updating.
*   **FPGA Challenge:** Implementing the weight-update equation requires careful fixed-point fractional math (Q-format) to prevent the filter from going unstable. You will heavily utilize the DSP48E1 slices for parallel Multiply-Accumulate (MAC) operations.
*   **The Demo:** You play loud white noise from a phone near the "noise" mic, and speak into the "speech" mic. The speakers output your clean voice. 
*   **Hardware to Buy:** 2x Digilent Pmod MIC3 (or Pmod I2S2).

## 3. Real-Time Voice Disguiser / Pitch Shifter (Phase Vocoder)
**The Concept:** You speak into a microphone, and the FPGA alters the pitch of your voice in real-time without changing the speed of your speech (e.g., sounding like Darth Vader or a chipmunk).
*   **Signal Processing:** Short-Time Fourier Transform (STFT), phase unwrapping, frequency scaling, and Inverse STFT.
*   **FPGA Challenge:** This is extremely Verilog-heavy. You must implement a streaming Fast Fourier Transform (FFT) block, manipulate the phase data in the frequency domain, and run an IFFT back to the time domain, all within milliseconds.
*   **The Demo:** The professor puts on headphones, speaks into the mic, and uses the Boolean Board's slide switches to change their voice pitch on the fly. Guaranteed to impress and entertain.
*   **Hardware to Buy:** 1x Digilent Pmod I2S2 (provides high-quality Audio In and Out).

## 4. Baseband OFDM Transceiver with Analog Loopback
**The Concept:** Orthogonal Frequency Division Multiplexing (OFDM) is the backbone of 4G/5G and Wi-Fi. You will build a complete digital transmitter and receiver, send the signal out of the FPGA as an analog wave through a physical wire, read it back in, and decode it.
*   **Signal Processing:** QAM mapping, IFFT (Transmitter), FFT (Receiver), Cyclic Prefix insertion/removal, channel estimation, and equalization.
*   **FPGA Challenge:** Managing the complex data path of an OFDM symbol. You will need to write Verilog for symbol synchronization and phase correction to recover the data.
*   **The Demo:** You stream a small image from your PC to the FPGA. The FPGA modulates it into OFDM, sends it over a noisy analog jumper wire, receives it, demodulates it, and sends the image back to the PC. You can pinch the wire to introduce "channel noise" and watch the Bit Error Rate (BER) go up on the 7-segment display.
*   **Hardware to Buy:** 1x Pmod DA4 (Digital to Analog) and 1x Pmod AD1 (Analog to Digital). 

## 5. Live Guitar Multi-Effects Processor
**The Concept:** Turn the Boolean Board into a professional digital guitar pedal. You will implement Distortion, Flanger, Delay, and Reverb. 
*   **Signal Processing:** Non-linear wave shaping (Distortion), fractional delay lines (Reverb/Delay), Low-Frequency Oscillators (LFO), and comb filtering (Flanger).
*   **FPGA Challenge:** Managing large circular buffers in BRAM for the echo/delay effects, and writing the LFO math to smoothly modulate the delay taps for the Flanger without audio artifacting (clicks/pops).
*   **The Demo:** Bring an electric guitar to the viva. Plug it into the board, plug the board into an amp, and play live while flipping the 16 slide switches to turn different effects on and off. 
*   **Hardware to Buy:** 1x Digilent Pmod I2S2, plus 1/4-inch to 3.5mm audio adapters for the guitar cables.

## 6. Real-Time 2D FFT Image Spectrum Analyzer
**The Concept:** Instead of filtering images in the spatial domain (like a simple Sobel filter), you bring the image into the 2D Frequency Domain. 
*   **Signal Processing:** 2D Fast Fourier Transform, frequency-domain low-pass/high-pass filtering, 2D IFFT.
*   **FPGA Challenge:** A 2D FFT requires doing 1D FFTs on all rows, transposing the matrix in memory, and doing 1D FFTs on all columns. This requires intense BRAM memory management and pipelining. 
*   **The Demo:** The HDMI output splits the screen in half. The left shows the 2D frequency spectrum of a camera feed or image. The right shows the filtered image. As you flip switches, you apply different frequency masks and instantly see the image change.
*   **Hardware to Buy:** None (uses UART and built-in HDMI), OR 1x Pmod Camera (like the OV7670) for live video.

## 7. Live ECG Arrhythmia Classifier (ML for Signal Processing)
**The Concept:** A wearable biomedical device that reads a real human heartbeat, extracts signal features, and runs a lightweight Neural Network to classify the heartbeat as "Normal" or "Arrhythmia".
*   **Signal Processing:** Pan-Tompkins filtering for noise removal, Wavelet Transform for feature extraction.
*   **FPGA Challenge:** You must design a custom hardware accelerator (MAC arrays) to run the neural network inference (e.g., a tiny Multi-Layer Perceptron) entirely in Verilog without a CPU.
*   **The Demo:** Connect sticky ECG electrode pads to a teammate. The raw ECG is drawn on the PC, but the Boolean Board processes the signal live, outputting the classification (Normal vs. Abnormal) on the 7-segment display.
*   **Hardware to Buy:** 1x Pmod AD1 and 1x AD8232 ECG Sensor module (very cheap on Amazon/Robocore).

---

## How to Choose

*   **Choose #1 (Beamforming)** if your team is excellent at math and logic timing.
*   **Choose #2 (LMS)** if you want a classic, bulletproof SP project with an undeniable "wow" factor.
*   **Choose #3 or #5 (Audio FX/Vocoder)** if anyone on the team is a musician or audiophile. 
*   **Choose #4 (OFDM)** if you are interested in telecommunications and want to work at Qualcomm/Samsung.
*   **Choose #7 (ECG + ML)** if you want to hit the "Machine Learning for SP" category mentioned in the flier and have a medical application.
