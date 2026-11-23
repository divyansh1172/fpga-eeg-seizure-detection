### PROJECT 4 — Real-Time Sobel Edge Detection on FPGA with HDMI Output

**B. Concept.** A test image is stored in the FPGA's on-chip memory; the FPGA computes the Sobel edge-detection operator (a classic gradient-based edge detector) on the image in hardware and displays the result live on an HDMI monitor, alongside (or toggled against) the original image — a strong, highly visual demo with **zero external hardware required.**

**C. Signal processing problem.**
- *Input:* a static grayscale test image, pre-loaded into BRAM (converted offline from a PNG/JPEG using a Python script into a `.coe`/`.mem` initialization file).
- *Problem:* detect edges (regions of rapid intensity change) — a 2D convolution problem.
- *Algorithm:* Sobel operator — two 3×3 convolution kernels (horizontal and vertical gradient), combined via gradient magnitude.
- *Output:* an edge map displayed over HDMI, with a switch to toggle between original and edge-detected view.
- *Concepts:* 2D convolution, spatial filtering, gradient-based feature detection, image buffering/streaming architecture, pipelining.

**D. Why it fits EE2000.** 2D convolution is the direct generalization of the 1D convolution/filtering you'll cover for audio/ECG signals elsewhere in the course — this project demonstrates that the same signal-processing principle (convolution with a kernel) applies across 1D and 2D signals, which is a genuinely valuable conceptual bridge to show in your report.

**E. Boolean Board implementation.**
```
Test image (offline) → Python script → .coe/.mem file → Vivado BRAM initialization
  → [FPGA] line-buffer + 3x3 window generator (streams the image pixel-by-pixel)
  → [FPGA] Sobel Gx, Gy convolution (DSP48 multiplies)
  → [FPGA] gradient magnitude approximation (|Gx| + |Gy|, avoiding a hardware sqrt)
  → [FPGA] threshold (optional, for a binary edge map)
  → [FPGA] HDMI display controller (timing generator + pixel output)
  → HDMI monitor
```
The convolution, line-buffering, and HDMI pixel-timing logic must all run on the FPGA — this is unambiguously a hardware project since the entire image pipeline, including video timing generation, is real digital design work, not just "display a precomputed image."

**F. Hardware requirements.**
- *Required:* Boolean Board; an HDMI monitor/cable (widely available, likely no purchase needed); **no Pmod purchase required** for the core project, since the image is stored on-chip rather than captured live.
- *Optional (extension only):* a Pmod or breakout camera module (e.g., OV7670-class) if you want to extend to live video input rather than a static test image — flagged as a stretch goal, not baseline scope, because of BRAM capacity constraints (see H below).

**G. Algorithm.**
```
Pixel stream → Line buffers (hold 2 previous rows) [moderate — classic streaming-image architecture]
             → 3x3 window formation [moderate]
             → Sobel Gx = [-1 0 1; -2 0 2; -1 0 1] convolution [easy once window exists]
             → Sobel Gy = [-1 -2 -1; 0 0 0; 1 2 1] convolution [easy once window exists]
             → |G| ≈ |Gx| + |Gy| [easy]
             → Threshold → binary edge map [easy]
             → HDMI pixel output, timed to display sync signals [hard — video timing must be cycle-exact]
```
The line-buffer/windowing architecture and HDMI timing generation are the genuinely hard parts — the Sobel math itself is simple once the pixel window exists.

**H. FPGA implementation challenges.**
- *Fixed-point:* pixel values are typically 8-bit grayscale; gradient sums need a few extra bits to avoid overflow (standard practice, well documented in the sources below).
- *Memory:* a QVGA (320×240) 8-bit grayscale test image is ~75 KB — fits comfortably within 337 KB BRAM alongside line buffers and a frame buffer for the processed output; a full-color or higher-resolution image will not fit and should be avoided or downsampled.
- *Pipelining:* the line-buffer + 3×3-window + convolution + HDMI-output chain must be carefully pipelined so that a new pixel is produced every clock cycle to keep up with the video timing — this is the main design/debug challenge.
- *DSP usage:* light — a handful of multiplies per pixel for the two kernels.
- *Realistic solution:* build and verify the line-buffer/windowing module in isolation first (with a testbench comparing against a Python "golden" 3×3 window extraction) before adding the Sobel math or HDMI output — debugging all three at once is a common failure mode.

**I. Software simulation.** Implement Sobel edge detection in Python (`scipy`/`numpy`, or OpenCV for comparison) on your chosen test image, visualize `Gx`, `Gy`, and the combined edge map, and generate a fixed-point-quantized version that bit-matches what your Verilog should produce, to use as your hardware testbench's golden reference.

**J. Experimental metrics.** Pixel-level match rate between your FPGA output and the Python golden reference (should be very high, ideally near-100% after fixed-point tuning); FPGA resource utilization (LUTs, DSP48, BRAM) as a function of image size; achieved pixel throughput/frame rate; (qualitative but valid) visual comparison of your Sobel result against a well-known reference implementation (e.g., OpenCV's `cv2.Sobel`).

**K. Literature.**
1. Irwin Sobel & Gary Feldman — original Sobel operator; typically cited via a standard image processing textbook (e.g., Gonzalez & Woods, *Digital Image Processing*) rather than a single paper, since it predates modern citation norms.
2. "Implementation and Optimization of FPGA-Based Edge Detection Algorithm," *Springer* (2021) — (cite index="61-1">combines the FPGA-based Sobel algorithm with VGA display technology, showing that compared to serial software processing, hardware processing is much faster while the accuracy of detection results is guaranteed</cite>. Very close match to your project's core architecture (adapt VGA specifics to your HDMI output).
3. "Implementation of Sobel Edge Detection Algorithm and VGA Display Based on FPGA," IEEE Xplore — (cite index="64-1">Verilog is used to design the Sobel algorithm and VGA display control code, with parallel processing achieving roughly 9x speedup over serial processing, verified on a Cyclone II FPGA</cite>. Directly reproducible architecture and a concrete, citable speedup figure.
4. "Parallel Processing of Sobel Edge Detection on FPGA: Enhancing Real-Time Image Analysis," PMC (2024) — (cite index="63-1">implements an improved Sobel edge detection algorithm in Verilog designed for real-time RGB image processing, applying horizontal and vertical Sobel kernels in parallel to compute gradient magnitudes over 3x3 pixel windows</cite>. Recent, freely accessible, useful for your extension work if you go to color images.
5. GitHub — Gowtham1729/Image-Processing (Basys3 FPGA) — (cite index="68-1">an image-processing toolbox for Basys3, using Verilog for hardware description and Python for image-to-binary (.coe file) conversion, loading images into FPGA Block RAM, and including Sobel edge detection among several selectable operations, with live VGA display</cite>. A genuinely useful open-source reference for the exact "image → .coe → BRAM → VGA/HDMI" pipeline you need — cite it as a design-pattern reference, and treat any code you consult from it as something to study and reimplement yourselves, not copy verbatim (both for the AI/authorship policy and for your own learning).

**L. Replication possibility.** Mid-term: reproduce Sobel edge detection in Python on your chosen test image and verify it visually/quantitatively matches a reference implementation (e.g., OpenCV). Final: your own contribution is the complete FPGA hardware pipeline (line-buffering, convolution, HDMI display) plus a resource-utilization and pixel-accuracy comparison against your Python golden reference — genuinely new engineering work, since the FPGA architecture must be built by you even though the algorithm itself is well-established.

**M. Extensions.**
1. Add a live toggle (switch) between original and edge-detected display, or a side-by-side split-screen view.
2. Implement a second edge operator (e.g., Prewitt or a simple Laplacian) and compare results/resource usage against Sobel.
3. Extend to a live camera input (Pmod camera module) instead of a static stored image — a genuine stretch goal given the BRAM/pipelining complexity increase.
4. Add basic noise-robustness testing: add synthetic noise to your test image in Python, and evaluate/display how Sobel's edge output degrades (ties into the noise-sensitivity point explicitly noted in the literature).

**N. Team-of-4 distribution.**
- *Member 1:* Literature review, algorithm/math writeup, test-image selection and preprocessing pipeline design.
- *Member 2:* Python golden-reference implementation, fixed-point quantization, all report plots/comparisons.
- *Member 3:* Verilog RTL for line-buffering/windowing + Sobel convolution, testbenches.
- *Member 4:* HDMI display controller/timing generation, hardware integration, demo setup.

**O. Expected difficulty: Moderate.** The Sobel math is easy; the video-timing and pipelined-streaming architecture is the genuinely challenging (and educational) part, and is well-documented enough in the literature that your team has a clear reference path.

**P. Time feasibility.**
- Literature review: 1 week
- Python golden reference + fixed-point spec: 1.5 weeks
- Line-buffer/windowing Verilog + testbench: 2 weeks
- Sobel convolution Verilog: 1 week
- HDMI display controller: 2 weeks (this is usually the single longest block for teams new to video timing)
- Integration + testing: 1.5 weeks
- Report/presentation: ongoing + 1 week
- **Flag:** HDMI timing generation is frequently underestimated by student teams — if your team has no prior video-timing experience, budget extra time here specifically, and consider using a simpler fixed test pattern first to validate your HDMI controller before wiring in the Sobel pipeline.
