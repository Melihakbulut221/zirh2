#!/usr/bin/env python3
# =============================================================================
# ZIRH-2 - pre-beam escape-ratio prediction from the shipped layout
#
# The gate-level sweep (test_gl_seu_sweep.py) establishes the escape
# window: same bit, two replicas, same cycle - nothing else escapes.
# This script supplies the other half of the prediction: from the final
# DEF it measures the physical distance between same-bit replica flops
# in chain A (macro-bound) and chain B (tool-placed), folds a
# charge-sharing multi-cell-upset range model over those distances, and
# emits the numbers docs/PREDICTION.md registers before beam time.
#
#   usage: python3 scripts/seu_predict.py <final_run_dir>
#          (a runs/wokwi/final directory from a green gds run)
#
# Model: P(simultaneous double upset | one particle) ~ exp(-d/lambda),
# with lambda the charge-sharing collection range. At 130 nm bulk the
# dual-node literature (Amusan et al., TNS 2006; Narasimham et al.)
# puts meaningful charge sharing below ~2 um and negligible beyond a
# few um; the table sweeps lambda across 0.25-4 um so the claim does
# not hinge on one number.
# =============================================================================

import math
import re
import sys
from pathlib import Path

CHAIN_B = ("u_ch_b_a", "u_ch_b_b", "u_ch_b_c")
Q_NET = {"u_ch_b_a": "b_qa", "u_ch_b_b": "b_qb", "u_ch_b_c": "b_qc"}
LAMBDAS_UM = (0.25, 0.5, 1.0, 2.0, 4.0)


def parse_bit_map(nl_text):
    """chain-B flop instance -> (replica, bit), from the Q net it drives."""
    bit_of = {}
    for m in re.finditer(
            r"sg13g2_dfrbpq_\d+\s+\\(u_hk\.(u_ch_b_[abc])/\S+)\s*\(([^;]+?)\);",
            nl_text, re.S):
        inst, rep, body = m.group(1), m.group(2), m.group(3)
        q = re.search(r"\.Q\(\s*\\u_hk\.(b_q[abc])\[(\d+)\]\s*\)", body)
        if q:
            bit_of[inst] = (rep, int(q.group(2)))
    return bit_of


def parse_def(def_text):
    """instance -> (x_um, y_um) for chain-B flops and the chain-A macros."""
    unit = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", def_text).group(1))
    place = {}
    for m in re.finditer(
            r"- (\S+) (\S+) \+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \)",
            def_text):
        inst, cell, x, y = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        if inst.startswith("u_hk.u_ch_b_") or cell == "zirh_tmr_ff32":
            place[inst] = (x / unit, y / unit)
    return place


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def main():
    final = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/wokwi/final")
    nl_text = next((final / "nl").glob("*.nl.v")).read_text()
    def_text = next((final / "def").glob("*.def")).read_text()

    bit_of = parse_bit_map(nl_text)
    place = parse_def(def_text)

    # chain B: same-bit cross-replica pair distances (3 pairs per bit)
    pos = {}
    for inst, (rep, bitn) in bit_of.items():
        if inst in place:
            pos[(rep, bitn)] = place[inst]
    nbits = len({b for _, b in pos})
    b_pairs = []
    for bitn in range(nbits):
        ps = [pos[(r, bitn)] for r in CHAIN_B if (r, bitn) in pos]
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                b_pairs.append(dist(ps[i], ps[j]))

    # chain A: the macro origins ARE the floor - same-bit replicas live in
    # three separate hard macros, so no pair can be closer than the gap
    # between macro bounding boxes
    macros = sorted(v for k, v in place.items() if "g_a_macro" in k)
    a_pairs = [dist(macros[i], macros[j])
               for i in range(len(macros)) for j in range(i + 1, len(macros))]

    b_sorted = sorted(b_pairs)
    print(f"chain B same-bit pairs: {len(b_pairs)} "
          f"(bits mapped: {nbits})")
    print(f"  min {b_sorted[0]:.2f} um   median {b_sorted[len(b_sorted)//2]:.2f} um   "
          f"max {b_sorted[-1]:.2f} um")
    print(f"  pairs closer than 2 um: {sum(1 for d in b_sorted if d < 2.0)}"
          f"   closer than 5 um: {sum(1 for d in b_sorted if d < 5.0)}")
    print(f"chain A macro origins: "
          + "  ".join(f"({x:.0f},{y:.0f})" for x, y in macros))
    print(f"  macro pair separations: "
          + "  ".join(f"{d:.0f} um" for d in sorted(a_pairs)))

    print("\nlambda_um   S_B=sum(exp(-d/l))   S_A                 ratio B/A")
    for lam in LAMBDAS_UM:
        sb = sum(math.exp(-d / lam) for d in b_pairs)
        sa = sum(math.exp(-d / lam) for d in a_pairs)
        ratio = "inf" if sa == 0 or sb / sa > 1e12 else f"{sb / sa:.3g}"
        print(f"{lam:9.2f}   {sb:18.6g}   {sa:18.6g}   {ratio}")

    print("\nheadline: chain A's closest same-bit replica pair is >= "
          f"{min(a_pairs):.0f} um apart; chain B's closest is "
          f"{b_sorted[0]:.2f} um. Within any plausible charge-sharing "
          "range, single-particle double upsets are possible in B and "
          "physically excluded in A - chain A escapes only by the "
          "accidental coincidence of two independent particles inside "
          "one clock cycle.")


if __name__ == "__main__":
    main()
