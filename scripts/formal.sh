#!/bin/bash
# =============================================================================
# ZIRH-2 - formal verification of the escape-window theorem
#
#   bash scripts/formal.sh [N ...]     default: 4 8 32
#
# For each ring width N:
#   1. containment - BMC (depth 24) then k-induction: under any upset
#      stream confined to one replica per cycle, the voted output equals
#      the golden ring in every bit of every cycle. UNSAT = theorem.
#   2. witness - a cover trace where one same-bit two-replica upset
#      escapes to the ring output; the VCD lands in formal/out/ and is
#      the mechanism drawn by the solver (GTKWave-ready).
#
# Tools: yosys (read_verilog -sv -formal, write_smt2), yosys-smtbmc, z3.
# =============================================================================

set -e
cd "$(dirname "$0")/.."
mkdir -p formal/out

NS=${@:-"4 8 32"}
YOSYS=${YOSYS:-yosys}
SMTBMC=${SMTBMC:-yosys-smtbmc}

for N in $NS; do
  echo "=== N=$N: containment (BMC + induction) ==="
  $YOSYS -q -p "
    read_verilog -sv -formal -DFORMAL src/zirh_tmr_lib.v formal/f_ring.sv
    chparam -set N $N f_ring
    prep -top f_ring
    write_smt2 formal/out/ring_n$N.smt2"
  $SMTBMC -s z3 --presat -t 24 formal/out/ring_n$N.smt2
  $SMTBMC -s z3 --presat -i -t 24 formal/out/ring_n$N.smt2
  echo "    PROVEN at N=$N (BMC clean, induction holds)"

  echo "=== N=$N: escape witness (cover) ==="
  $YOSYS -q -p "
    read_verilog -sv -formal -DFORMAL -DF_PAIR src/zirh_tmr_lib.v formal/f_ring.sv
    chparam -set N $N f_ring
    prep -top f_ring
    write_smt2 formal/out/pair_n$N.smt2"
  $SMTBMC -s z3 --presat -c -t $((N + 6)) \
      --dump-vcd formal/out/escape_n$N.vcd formal/out/pair_n$N.smt2
  echo "    WITNESS at N=$N: formal/out/escape_n$N.vcd"
done

echo "formal: all ring widths proven, witnesses dumped"
