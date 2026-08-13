#!/bin/bash
# =============================================================================
# ZIRH - lint gate (H41): verilator --lint-only over the project RTL
#
#   bash scripts/lint.sh
#
# Lints the ZIRH-authored RTL (src/zirh_*.v + the top) as one design
# with the vendored SERV and the PDK SRAM behavioral models included
# for resolution. Waivers, each with its reason:
#   UNUSEDSIGNAL/UNUSEDPARAM  the _unused reduction idiom and spare
#                             port bits are deliberate
#   BLKSEQ                    blocking temps inside clocked blocks and
#                             function bodies (b in the SpW encoder,
#                             the SECDED helpers) are scoped and read
#                             before any nonblocking consumer
#   WIDTHEXPAND               context widening is Verilog semantics
#   PINCONNECTEMPTY           intentionally open outputs
#   PINMISSING/DECLFILENAME/  vendored SERV and PDK models are not
#   EOFNEWLINE/VARHIDDEN      rewritten to please a linter
# Gate: verilator must exit 0 AND no remaining warning may point into
# zirh-authored files. LATCH, WIDTHTRUNC, BLKANDNBLK and the rest of
# -Wall stay ARMED - the first run caught a real mixed-assignment in
# the SpaceWire encoder with exactly this gate.
# =============================================================================
set -eo pipefail
cd "$(dirname "$0")/.."

VL=${VERILATOR:-verilator}
SRAM_V=${PDK_ROOT:?set PDK_ROOT}/ihp-sg13g2/libs.ref/sg13g2_sram/verilog

$VL --lint-only -Wall --timing \
    -Wno-DECLFILENAME -Wno-VARHIDDEN -Wno-EOFNEWLINE \
    -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-BLKSEQ \
    -Wno-WIDTHEXPAND -Wno-PINCONNECTEMPTY -Wno-PINMISSING \
    -DFUNCTIONAL -DZIRH_SIM_ENV \
    -Isrc \
    --top-module tt_um_hma_zirh2 \
    src/serv/*.v \
    "$SRAM_V"/RM_IHPSG13_1P_core_behavioral_bm_bist.v \
    "$SRAM_V"/RM_IHPSG13_1P_1024x8_c2_bm_bist.v \
    src/zirh_*.v src/tt_um_hma_zirh2.v \
    2>&1 | tee /tmp/zirh_lint.log

# gate: warnings that point into zirh-authored files fail the build
if grep -E "%Warning" /tmp/zirh_lint.log | grep -E "zirh_|tt_um_hma" \
     | grep -v "src/serv/"; then
  echo "lint: warnings in ZIRH-authored RTL - failing"
  exit 1
fi
echo "lint: zirh-authored RTL is warning-clean"
