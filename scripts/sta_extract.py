#!/usr/bin/env python3
# =============================================================================
# sta_extract - pull the sweep verdict out of a finished LibreLane run
#
#   python3 scripts/sta_extract.py runs/wokwi [--json out.json]
#
# Collects, per corner: setup/hold worst slack and violation counts,
# worst setup/hold clock skew, plus every hold path that touches the
# chain-A macros (min.rpt paths mentioning g_a_macro) with its slack -
# the macro-crossing margins SCOPE flagged as the open item. Exits
# nonzero if any corner has negative hold or setup slack, so a sweep
# job's pass/fail IS the timing verdict.
# =============================================================================

import argparse
import json
import re
import sys
from pathlib import Path


def find_sta_dir(run_dir):
    cands = sorted(Path(run_dir).glob("*-openroad-stapostpnr"))
    if not cands:
        sys.exit(f"no stapostpnr step under {run_dir}")
    return cands[-1]


def corner_summary(cdir):
    out = {}
    for name, rpt in (("setup_skew", "skew.max.rpt"),
                      ("hold_skew", "skew.min.rpt")):
        p = cdir / rpt
        if p.exists():
            m = re.search(r"(-?\d+\.\d+)", p.read_text())
            out[name] = float(m.group(1)) if m else None
    return out


def macro_clk_latency(cdir):
    """Chain-A macro clock arrivals from clock.rpt, when the report's
    extreme-latency endpoints happen to be macro pins - partial coverage
    of the cross-macro skew question; a dedicated STA step would give
    all three pins."""
    p = cdir / "clock.rpt"
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text().splitlines():
        m = re.match(r"\s*(-?\d+\.\d+)?\s*(-?\d+\.\d+)?\s+network latency\s+(\S*g_a_macro\S*)", line)
        if m:
            val = m.group(1) or m.group(2)
            out[m.group(3)] = float(val)
    return out


def macro_hold_paths(cdir):
    """Every hold path in min.rpt that touches a chain-A macro, with its
    slack - the as-built cost of the placement-separation experiment."""
    p = cdir / "min.rpt"
    if not p.exists():
        return []
    paths = []
    block = []
    touches = False
    for line in p.read_text().splitlines():
        if line.startswith("Startpoint:"):
            block, touches = [line], "g_a_macro" in line
        elif block:
            block.append(line)
            if "g_a_macro" in line:
                touches = True
            m = re.match(r"\s*(-?\d+\.\d+)\s+slack", line)
            if m:
                if touches:
                    start = block[0].split()[1]
                    end = next((l.split()[1] for l in block
                                if l.startswith("Endpoint:")), "?")
                    paths.append({"start": start, "end": end,
                                  "slack": float(m.group(1))})
                block, touches = [], False
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--json")
    ap.add_argument("--metrics", help="final metrics.json (default: "
                                      "<run_dir>/final/metrics.json)")
    args = ap.parse_args()

    run = Path(args.run_dir)
    metrics_path = Path(args.metrics) if args.metrics \
        else run / "final" / "metrics.json"
    metrics = json.loads(metrics_path.read_text())

    sta = find_sta_dir(run)
    corners = {}
    for cdir in sorted(sta.iterdir()):
        if not cdir.is_dir():
            continue
        c = cdir.name
        corners[c] = {
            "setup_ws": metrics.get(f"timing__setup__ws__corner:{c}"),
            "hold_ws": metrics.get(f"timing__hold__ws__corner:{c}"),
            "setup_vio": metrics.get(f"timing__setup_vio__count__corner:{c}"),
            "hold_vio": metrics.get(f"timing__hold_vio__count__corner:{c}"),
            **corner_summary(cdir),
        }
        lat = macro_clk_latency(cdir)
        if lat:
            corners[c]["macro_clk_latency"] = lat
        mp = macro_hold_paths(cdir)
        if mp:
            corners[c]["macro_hold_paths"] = sorted(
                mp, key=lambda p: p["slack"])[:10]
            corners[c]["macro_hold_worst"] = min(p["slack"] for p in mp)

    report = {
        "utilization": metrics.get("design__instance__utilization"),
        "setup_ws": metrics.get("timing__setup__ws"),
        "hold_ws": metrics.get("timing__hold__ws"),
        "corners": corners,
    }

    bad = []
    for c, d in corners.items():
        for k in ("setup_ws", "hold_ws"):
            v = d.get(k)
            if v is not None and v < 0:
                bad.append(f"{c}:{k}={v:.4f}")

    print(f"util {report['utilization']:.3f}  "
          f"setup {report['setup_ws']:+.3f}  hold {report['hold_ws']:+.4f}")
    for c, d in corners.items():
        line = (f"  {c:24s} setup {d['setup_ws']:+8.3f} ({d['setup_vio']}) "
                f"hold {d['hold_ws']:+8.4f} ({d['hold_vio']})")
        if "macro_hold_worst" in d:
            line += f"  macroA-hold-worst {d['macro_hold_worst']:+.4f}"
        print(line)

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))

    if bad:
        print("TIMING VIOLATIONS: " + ", ".join(bad))
        sys.exit(1)
    print("sweep point: PASS")


if __name__ == "__main__":
    main()
