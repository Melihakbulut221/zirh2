# =============================================================================
# ZIRH-2 - explicit PNR SDC (PROGRAM.md, placement campaign round 8)
#
# The flow warned on every run: 'PNR_SDC_FILE' is not defined, using
# generic fallback. That fallback pins max_fanout at 10, and the
# MAX_FANOUT_CONSTRAINT variable proved to be a wheel connected to
# nothing (identical 401 violations / 2002 buffers across two runs).
# This file is the same constraint set with the one number this die
# needs changed: at 20 MHz with +22 ns of setup slack, fanout 16 costs
# delay the design cannot even feel, and it halves a buffer bill the
# floorplan cannot house. Signoff STA keeps its own SDC - this file
# constrains construction, not the verdict.
# =============================================================================

create_clock -name clk -period 40 [get_ports clk]

# inputs enumerated explicitly: the sdc interpreter in the construction
# steps has no remove_from_collection (measured, round 8)
set_input_delay  8 -clock clk [get_ports {rst_n ena ui_in[*] uio_in[*]}]
set_output_delay 8 -clock clk [all_outputs]

set_max_fanout 16 [current_design]
