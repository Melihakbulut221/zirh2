#!/usr/bin/env bash
# =============================================================================
# ZIRH - synthesis integrity check for TMR structures
#
#   bash scripts/check_tmr.sh
#
# WHY THIS EXISTS
#   Passing simulation does not prove a TMR structure survives synthesis.
#   Three identical registers driven by identical logic are, to an optimiser,
#   one register. Yosys will happily collapse them and the resulting netlist
#   simulates identically - the hardening is simply gone.
#
#   The RTL defends against this by giving every replica its own
#   (* keep_hierarchy *) module (see src/zirh_tmr_lib.v). This script is the
#   proof that the defence is still working: it synthesises each block and
#   counts the replica instances and flip-flops that actually survive.
#
#   Measured on the current RTL:
#     with the attributes    -> 79 FFs in zirh_clk_rst  (TMR intact)
#     attributes stripped    -> 26 FFs                  (TMR gone, err_o
#                                                        constant-folded away)
#
# NOTES
#   - Synthesis stops before ABC. ABC is a technology mapper; replica merging
#     happens in the earlier opt/opt_merge passes, so no liberty file or PDK
#     is needed and the check runs in well under a second.
#   - -flatten is passed deliberately: it mimics the LibreLane flow and is
#     exactly the condition under which keep_hierarchy has to hold.
#   - Known fragility, not covered by the pass/fail below: an explicit
#     `opt_merge -share_all` still collapses the replicas despite
#     keep_hierarchy. That pass is not part of the standard flow, but do not
#     add it to a synthesis script.
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/src"

if ! command -v yosys >/dev/null 2>&1; then
    echo "ERROR: yosys not found in PATH" >&2
    exit 127
fi

failures=0

# ---------------------------------------------------------------------------
# run_check <label> <top> <expected_replica_instances> <expected_ffs>
#           <replica_module> <source files...>
#
# Synthesises <top> and verifies that <expected_replica_instances> instances
# of <replica_module> and <expected_ffs> flip-flops survive optimisation.
# ---------------------------------------------------------------------------
run_check() {
    local label="$1" top="$2" exp_rep="$3" exp_ff="$4" rep_mod="$5"
    shift 5
    local files=("$@")

    local read_cmds=""
    for f in "${files[@]}"; do
        read_cmds+="read_verilog -sv -DZIRH_SIM_ENV ${SRC}/${f}; "
    done

    local script="${read_cmds}
        ${EXTRA_CMDS:-}
        hierarchy -check -top ${top};
        synth -top ${top} -flatten -run begin:fine;
        opt -full;
        memory_map;
        techmap;
        opt -full;
        select -count t:*${rep_mod}*;
        stat -top ${top};"

    local out
    if ! out="$(yosys -p "${script}" 2>&1)"; then
        echo "  FAIL  ${label}: yosys returned an error"
        echo "${out}" | tail -5 | sed 's/^/        /'
        failures=$((failures + 1))
        return
    fi

    # Replica instances: "select -count" prints "<N> objects.".
    # It counts cells per module DEFINITION, which is what we want here -
    # each replica is a separate cell in the parent module.
    local got_rep
    got_rep="$(echo "${out}" | grep -oE '^[0-9]+ objects\.$' | grep -oE '^[0-9]+' | head -1)"

    # Flip-flops: taken from the LAST section of `stat`. When the design still
    # has hierarchy that is the "design hierarchy" summary, which multiplies
    # each submodule's cells by its instance count - a plain `select -count`
    # would undercount, since it sees each module definition only once no
    # matter how many times it is instantiated. When everything collapsed into
    # a single module there is no hierarchy summary, and the last section is
    # the top module itself; summing there still reports the real number
    # instead of a misleading zero.
    local got_ff
    got_ff="$(echo "${out}" | awk '/^=== /{s=0} /DFF/{s+=$NF} END{print s+0}')"

    if [ -z "${got_rep}" ]; then
        echo "  FAIL  ${label}: could not parse replica count from yosys output"
        failures=$((failures + 1))
        return
    fi

    local ok=1

    if [ "${got_rep}" -ne "${exp_rep}" ]; then
        echo "  FAIL  ${label}: ${rep_mod} instances = ${got_rep}, expected ${exp_rep}"
        if [ "${got_rep}" -lt "${exp_rep}" ]; then
            echo "        replicas were MERGED - the TMR in ${top} is gone"
        fi
        ok=0
    fi

    if [ "${got_ff}" -ne "${exp_ff}" ]; then
        echo "  FAIL  ${label}: flip-flop count = ${got_ff}, expected ${exp_ff}"
        ok=0
    fi

    if [ "${ok}" -eq 1 ]; then
        echo "  ok    ${label}: ${got_rep}x ${rep_mod}, ${got_ff} FFs"
    else
        failures=$((failures + 1))
    fi
}

echo "ZIRH synthesis integrity check"
echo "------------------------------"

# --- check 1: the TMR register itself -------------------------------------
# zirh_tmr_reg at the default WIDTH=8:
#   3 replica instances, 3 x 8 = 24 data FFs + 1 err_o FF = 25 FFs.
run_check "zirh_tmr_reg  (TMR register replicas)" \
    zirh_tmr_reg 3 25 zirh_tmr_ff \
    zirh_tmr_lib.v

# --- check 2: the clock/reset block ---------------------------------------
# zirh_clk_rst at the default HB_BIT=23 (CW = 24):
#   3 reset-synchronizer replicas x 2 FFs        =  6
#   3 counter replicas x 24 bits                 = 72
#   1 err_hb_o FF                                =  1
#                                                  --
#                                                  79
run_check "zirh_clk_rst  (reset-sync replicas)" \
    zirh_clk_rst 3 79 zirh_rst_sync_rep \
    zirh_tmr_lib.v zirh_clk_rst.v

# --- check 3: the UART -----------------------------------------------------
# zirh_rs422 at the default DIV=174:
#   4 TMR registers in 2 parameterizations (WIDTH=4 and WIDTH=8), so the
#   library expands to 2 zirh_tmr_ff paramods x 3 replicas = 6 instances.
#   FFs: (4+8) x 2 directions x 3 replicas = 72 TMR data
#        + 4 err_o                          =  4
#        + shift/sync/capture (unprotected) = 31   -> 107 total
run_check "zirh_rs422    (UART TMR counters)" \
    zirh_rs422 6 107 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_rs422.v

# --- check 6: the ZIRH-2 bus interconnect ----------------------------------
# zirh_bus at the default TIMEOUT_LOG2=6: the ack watchdog is the only
# state - 1 zirh_tmr_ff paramod x 3 replicas, 6x3 = 18 + 1 err = 19 FFs.
run_check "zirh_bus      (watchdog replicas)" \
    zirh_bus 3 19 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_bus.v

# --- check 7: the ZIRH-2 UART register block --------------------------------
# zirh_uart_regs at RESET_DIV=174: the wrapped rs422 runs DIVW=16, so its
# 4 TMR counters are 2 paramods (w4, w16) + the BAUD register (w16) = 3
# paramods x 3 = 9 instances.
#   FFs: rs422 @16b: (4+16)x2x3=120 TMR + 4 err + 31 plain   = 155
#        + BAUD 16x3 + 1 err                                 =  49
#        + sw slot 9 + rx buffer/flags 11                    =  20  -> 224
run_check "zirh_uart_regs (cmd path replicas)" \
    zirh_uart_regs 9 224 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_rs422.v zirh_uart_regs.v

# --- check 8: the ZIRH-2 ECC RAM --------------------------------------------
# zirh_ecc_ram: deliberately ZERO TMR replicas - the protection is the
# SECDED code itself. 16 words x 39 stored bits = 624 + 2 event FFs = 626.
run_check "zirh_ecc_ram  (SECDED, no TMR by design)" \
    zirh_ecc_ram 0 626 zirh_tmr_ff \
    zirh_ecc_ram.v

# --- check 9: the ZIRH-2 SoC cluster ----------------------------------------
# The ROM default is now the committed src/rom_init.vh (real firmware), so
# no chparam is needed - the empty-ROM vacuity trap (SERV constant-folding
# to 260 FFs, measured) is structurally gone.
#   12 replica instances = uart_regs 9 + bus watchdog 3.
#   FFs: SERV core+RF 1253 (RF 32x32 = 1024, PLAIN - the honest v1 story:
#   the CPU is itself a beam target) + eram 1250 + uregs 224 + bus 19
#   + glue 35 (incl. the cpu_awake X-gate), eram at 64 B = 2160.
#   NOTE: this number is FIRMWARE-DEPENDENT - the ROM contents are real
#   constants and SERV optimizes against them, so a firmware change can
#   legitimately move it by a few flops. Update it together with rom_init.vh.
run_check "zirh_soc      (SERV + P0 cluster)" \
    zirh_soc 12 2160 zirh_tmr_ff \
    serv/serv_aligner.v serv/serv_alu.v serv/serv_bufreg2.v \
    serv/serv_bufreg.v serv/serv_compdec.v serv/serv_csr.v \
    serv/serv_ctrl.v serv/serv_decode.v serv/serv_immdec.v \
    serv/serv_mem_if.v serv/serv_rf_if.v serv/serv_rf_ram_if.v \
    serv/serv_rf_ram.v serv/serv_rf_top.v serv/serv_state.v \
    serv/serv_top.v zirh_tmr_lib.v zirh_rom.v zirh_bus.v \
    zirh_ecc_ram.v zirh_rs422.v zirh_uart_regs.v zirh_soc.v
EXTRA_CMDS=""

# --- check 10: the ZIRH-2 housekeeping block --------------------------------
# zirh_hk at N=64 with the v2.1 additions (bus-timeout, frame-error and
# BOOT counters + the CPU watchdog): 25 replica-bearing paramods x
# instances. FFs: rings 448 + counters 363 + watchdog 67 + infra/misc
# + the two env strobe one-shots = 933.
run_check "zirh_hk       (A/B chains + counters)" \
    zirh_hk 25 933 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_tmr_ff64.v zirh_hk.v

# --- check 11: the telemetry framer v2 --------------------------------------
# zirh_tlm2 at INTERVAL_LOG2=16: interval 16 + state 6 = 2 paramods x 3 = 6
# instances. FFs: 22x3 TMR = 66 + 2 err + 121 snapshot/seq/chk = 189.
run_check "zirh_tlm2     (framer v2 replicas)" \
    zirh_tlm2 6 213 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_tlm2.v

# --- check 12: the environment monitor --------------------------------------
# zirh_env: window(11) + set(8) + btim(5) + burst(8) TMR regs; set and
# burst share the WIDTH=8 paramod DEFINITION, and select counts cells per
# definition - so 3 definitions x 3 replicas = 9, not 12 (the same gotcha
# the header documents). FFs: TMR (11+8+5+8)x3 = 96 + one err flop per
# reg = 4 + ripple 16 + rearm/tpulse/sync/evt glue 9 = 125. The
# oscillator and catch chain are behavioral under ZIRH_SIM_ENV
# (hand-instantiated cells otherwise); the ripple counter is shared RTL
# so this count matches the silicon netlist.
run_check "zirh_env      (TID + SET + burst)" \
    zirh_env 9 125 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_env.v

# --- check 13: the CAN node --------------------------------------------------
# zirh_can: TX + RX protocol FSM (WIDTH=3, shared definition) + three 8-bit
# counters (shared WIDTH=8 definition) = 2 definitions x 3 = 6 cells.
run_check "zirh_can      (protocol FSMs + counters)" \
    zirh_can 6 220 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_can.v

# --- check 14: the SpaceWire link --------------------------------------------
# zirh_spw: link FSM (3) + NULL and error counters (8) = 2 defs x 3 = 6.
run_check "zirh_spw      (link FSM + counters)" \
    zirh_spw 6 151 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_spw.v

# --- check 15: the interface block -------------------------------------------
# zirh_ifc: can + spw definitions plus the WIDTH=1 link-enable = 3 defs x 3.
run_check "zirh_ifc      (CAN + SpW + bus regs)" \
    zirh_ifc 9 376 zirh_tmr_ff \
    zirh_tmr_lib.v zirh_can.v zirh_spw.v zirh_ifc.v

# --- check 16: the ZIRH-2 top -----------------------------------------------
# FFs: soc 2160 + hk 933 + tlm2 213 + env 125 + ifc 376 + clk_rst 79
# + glue = 3887. Replicas: v2.2's 46 + the ifc's one NEW definition
# (WIDTH=3 FSM states) x 3 = 49; widths 1 and 8 reuse existing defs.
run_check "tt_um_hma_zirh2 (ZIRH-2 top)" \
    tt_um_hma_zirh2 49 3887 zirh_tmr_ff \
    serv/serv_aligner.v serv/serv_alu.v serv/serv_bufreg2.v \
    serv/serv_bufreg.v serv/serv_compdec.v serv/serv_csr.v \
    serv/serv_ctrl.v serv/serv_decode.v serv/serv_immdec.v \
    serv/serv_mem_if.v serv/serv_rf_if.v serv/serv_rf_ram_if.v \
    serv/serv_rf_ram.v serv/serv_rf_top.v serv/serv_state.v \
    serv/serv_top.v zirh_tmr_lib.v zirh_tmr_ff64.v zirh_clk_rst.v \
    zirh_rom.v zirh_bus.v zirh_ecc_ram.v zirh_rs422.v zirh_uart_regs.v \
    zirh_soc.v zirh_hk.v zirh_tlm2.v zirh_env.v zirh_can.v zirh_spw.v \
    zirh_ifc.v tt_um_hma_zirh2.v
EXTRA_CMDS=""

echo "------------------------------"
if [ "${failures}" -eq 0 ]; then
    echo "PASS: all hardening structures survived synthesis"
    exit 0
else
    echo "FAIL: ${failures} check(s) failed - hardening structures did NOT survive"
    exit 1
fi
