# ==============================================================================
# EE2000 Signal Processing (Fall 2026) - Team 15
# Batch Vivado Non-Project Synthesis & Implementation Script
# Target: AMD Spartan-7 XC7S50 (xc7s50csga324-1) on RealDigital Boolean Board
# Author: Member 4 (Vivado Implementation Lead)
# AI-assisted: Yes (scaffolding generated with Antigravity, reviewed by Member 4)
# ==============================================================================

set PROJ_DIR [file normalize [file join [file dirname [info script]] "../.."]]
set RTL_DIR  [file join $PROJ_DIR "rtl"]
set RES_DIR  [file join $PROJ_DIR "results"]
set XDC_FILE [file join $PROJ_DIR "endsem report/rtl/boolean_board.xdc"]

puts "=============================================================================="
puts "Starting EE2000 Seizure Detector Non-Project Vivado Flow"
puts "Project Directory : $PROJ_DIR"
puts "Target Device     : xc7s50csga324-1"
puts "=============================================================================="

# Create results directory if missing
file mkdir $RES_DIR

# 1. Read Synthesizable Verilog Source Files
puts "\n--> Reading Verilog RTL Sources..."
read_verilog [glob -nocomplain [file join $RTL_DIR "*.v"]]

# 2. Read Physical XDC Constraints
puts "\n--> Reading Board Pin & Timing Constraints..."
read_xdc $XDC_FILE

# 3. Logic Synthesis
puts "\n--> Running Logic Synthesis (Top: top_seizure_detector)..."
synth_design -top top_seizure_detector -part xc7s50csga324-1 -flatten_hierarchy rebuilt

# Check post-synthesis utilization
report_utilization -file [file join $RES_DIR "vivado_synth_utilization.rpt"]

# 4. Logic Optimization & Placement
puts "\n--> Running Logic Optimization and Placement..."
opt_design
place_design
phys_opt_design

# Post-place timing check
report_timing_summary -file [file join $RES_DIR "vivado_place_timing.rpt"]

# 5. Routing
puts "\n--> Running Routing..."
route_design

# 6. Post-Routing Reports (Utilization, Timing, Power)
puts "\n--> Generating Final Post-Implementation Reports..."
report_utilization -file [file join $RES_DIR "vivado_utilization_placed.rpt"]
report_timing_summary -max_paths 10 -file [file join $RES_DIR "vivado_timing_summary.rpt"]
report_power -file [file join $RES_DIR "vivado_power_report.rpt"]
report_drc -file [file join $RES_DIR "vivado_drc_routed.rpt"]

# 7. Bitstream Generation
puts "\n--> Generating FPGA Bitstream (top_seizure_detector.bit)..."
write_bitstream -force [file join $RES_DIR "top_seizure_detector.bit"]

puts "\n=============================================================================="
puts "Vivado Implementation Flow COMPLETED Successfully!"
puts "Bitstream generated : [file join $RES_DIR top_seizure_detector.bit]"
puts "Reports saved under : $RES_DIR"
puts "=============================================================================="
exit
