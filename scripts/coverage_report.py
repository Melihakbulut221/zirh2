#!/usr/bin/env python3
# =============================================================================
# ZIRH - functional coverage gate (H42)
#
#   python3 scripts/coverage_report.py          report + gate
#
# Two halves of the H42 ask:
#   FSM transitions   the unit suites record every observed (from,to)
#                     pair per product-program FSM (test/cov/*.json);
#                     this gate demands the EXPECTED set was seen -
#                     an FSM arc no test drives is a hole, and a hole
#                     fails the build
#   voter injections  every-voter-injected is owned by the R1/R16
#                     requirements (exhaustive GL sweep + library flip
#                     suites) and enforced by trace_check + the suites
#                     themselves; restated here for the report reader
#
# Line/branch coverage is registered follow-up work pending the
# Verilator-simulation migration; this gate covers what the brief
# names first: every FSM transition seen.
# =============================================================================

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent

# expected transition sets, from the RTL state encodings; arcs INTO a
# tag's reset state are always legal (POR between test scenarios)
RESET = {"sram39": 0, "boot": 0, "bist": 0, "dbg": 0}
EXPECTED = {
    "sram39": {  # IDLE=0 RD=1 SCRUB_RD=2 SCRUB_FIX=3
        (0, 1), (1, 0), (0, 2), (2, 3), (3, 0),
    },
    "boot": {    # STRAP=0 GOLDEN=1 HDR=2 LOAD=3 VERIFY=4 RUN=5
        (0, 1),          # golden strap
        (0, 2),          # any load strap
        (2, 3),          # header accepted
        (2, 1),          # header rejected, no fallback bank
        (3, 4),          # payload done
        (4, 5),          # commit
        (4, 1),          # verify failed, no fallback bank
        (5, 2),          # ISP reload while running
        (5, 1),          # watchdog ladder exhausted
    },
    "bist": {    # IDLE=0 RD=1 CHK=2 WR=3 ADV=4 DONE=5
        (0, 1), (0, 3),  # scan entry, march/fill entry
        (1, 2),          # read -> check
        (2, 3), (2, 4),  # check -> write (march), check -> advance
        (3, 4),          # write -> advance
        (4, 1), (4, 3),  # advance -> next read / next write
        (4, 5),          # done
        (5, 0),          # rearm
    },
    "dbg": {     # SAMPLE=0 OPEN=1 LOCKED=2
        (0, 1), (0, 2),
    },
}

fails = 0
for tag, expected in EXPECTED.items():
    path = root / "test" / "cov" / f"{tag}.json"
    if not path.exists():
        print(f"FAIL {tag}: no coverage record (suite not run?)")
        fails += 1
        continue
    seen = {tuple(t) for t in json.loads(path.read_text())}
    rst = RESET[tag]
    por = {a for a in seen if a[1] == rst and a not in expected}
    missing = expected - seen
    extra = seen - expected - por
    pct = 100 * (len(expected) - len(missing)) / len(expected)
    print(f"{tag}: {len(expected) - len(missing)}/{len(expected)} "
          f"expected arcs seen ({pct:.0f}%)"
          + (f", POR arcs: {sorted(por)}" if por else "")
          + (f", extra observed: {sorted(extra)}" if extra else ""))
    for arc in sorted(missing):
        print(f"  MISSING arc {arc[0]}->{arc[1]}")
        fails += 1
    # an arc outside the expected set means the map or the RTL moved
    for arc in sorted(extra):
        print(f"  FAIL unexpected arc {arc[0]}->{arc[1]} - update the "
              "map or explain the transition")
        fails += 1

print(f"coverage: {'FAIL' if fails else 'PASS'} ({fails} findings)")
sys.exit(1 if fails else 0)
