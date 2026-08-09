# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = zirh_tmr_lib.v
PROJECT_SOURCES += serv/serv_aligner.v
PROJECT_SOURCES += serv/serv_alu.v
PROJECT_SOURCES += serv/serv_bufreg.v
PROJECT_SOURCES += serv/serv_bufreg2.v
PROJECT_SOURCES += serv/serv_compdec.v
PROJECT_SOURCES += serv/serv_csr.v
PROJECT_SOURCES += serv/serv_ctrl.v
PROJECT_SOURCES += serv/serv_decode.v
PROJECT_SOURCES += serv/serv_immdec.v
PROJECT_SOURCES += serv/serv_mem_if.v
PROJECT_SOURCES += serv/serv_rf_if.v
PROJECT_SOURCES += serv/serv_rf_ram.v
PROJECT_SOURCES += serv/serv_rf_ram_if.v
PROJECT_SOURCES += serv/serv_rf_top.v
PROJECT_SOURCES += serv/serv_state.v
PROJECT_SOURCES += serv/serv_synth_wrapper.v
PROJECT_SOURCES += serv/serv_top.v
PROJECT_SOURCES += zirh_tmr_ff32.v
PROJECT_SOURCES += zirh_clk_rst.v
PROJECT_SOURCES += zirh_rom.v
PROJECT_SOURCES += zirh_bus.v
PROJECT_SOURCES += zirh_ecc_ram.v
PROJECT_SOURCES += zirh_rs422.v
PROJECT_SOURCES += zirh_uart_regs.v
PROJECT_SOURCES += zirh_soc.v
PROJECT_SOURCES += zirh_hk.v
PROJECT_SOURCES += zirh_tlm2.v
PROJECT_SOURCES += zirh_env.v
PROJECT_SOURCES += zirh_can.v
PROJECT_SOURCES += zirh_spw.v
PROJECT_SOURCES += zirh_ifc.v
PROJECT_SOURCES += zirh_tlm_mirror.v
PROJECT_SOURCES += tt_um_hma_zirh2.v

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
# behavioral oscillator/chain models - the real cell loops would hang
# zero-delay simulation (gate level keeps them but never enables the RO)
COMPILE_ARGS    += -DZIRH_SIM_ENV

else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
# the pinned cell models drive their internal delayed_* nets from specify
# blocks; icarus ignores specify by default and the flops never clock
# (measured: the whole die reads X forever) - -gspecify turns them on
COMPILE_ARGS    += -gspecify
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v
# newer PDK builds split the UDP primitives out of the cell models; the
# pinned build is self-contained - include the file only when it exists
VERILOG_SOURCES += $(wildcard $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_udp.v)
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
# the chain-A macros are blackboxes in the top netlist; their own gate
# netlist ships with the hardened deliverables
VERILOG_SOURCES += $(PWD)/../macro/hardened32/zirh_tmr_ff32.nl.v

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# List test modules to run, separated by commas and without the .py suffix.
# Gate-level runs add the netlist fault campaign - the contract on the
# netlist that flies; in RTL runs the module self-skips.
ifeq ($(GATES),yes)
COCOTB_TEST_MODULES = test,test_gl_campaign
else
COCOTB_TEST_MODULES = test
endif

# include cocotb's make rules to take care of the simulator setup
# rom_init.vh is an include, invisible to VERILOG_SOURCES: without this extra
# dependency a regenerated ROM silently reuses a stale sim.vvp (measured -
# the old mask kept answering the old checksum after a firmware rebuild)
CUSTOM_COMPILE_DEPS += $(SRC_DIR)/rom_init.vh

include $(shell cocotb-config --makefiles)/Makefile.sim
