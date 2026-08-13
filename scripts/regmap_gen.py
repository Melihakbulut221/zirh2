#!/usr/bin/env python3
# =============================================================================
# ZIRH - regmap generator and sync gate (H47)
#
#   python3 scripts/regmap_gen.py            regenerate docs/REGMAP.md
#                                            and fw/zirh_regs.h
#   python3 scripts/regmap_gen.py --check    regenerate to temp, diff
#                                            against committed, fail on
#                                            drift; also cross-check
#                                            fw/zirh.h addresses
#
# Deliberately dependency-free YAML subset parser (same policy as
# trace_check.py): the map's shape is fixed, the gate must run on bare
# python3 forever.
# =============================================================================

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent


def parse(text):
    blocks = []
    cur = None
    reg = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = re.match(r"  - name: (\S+)", line)
        if m:
            cur = {"name": m.group(1), "regs": [], "attrs": {}}
            blocks.append(cur)
            reg = None
            continue
        if cur is None:
            continue
        m = re.match(r"    (base|size|window|description): (.+)", line)
        if m and reg is None:
            cur["attrs"][m.group(1)] = m.group(2)
            continue
        m = re.match(r"      - \{name: (\w+), offset: (0x[0-9A-Fa-f]+), "
                     r"access: (\w+)", line)
        if m:
            reg = {"name": m.group(1), "offset": int(m.group(2), 16),
                   "access": m.group(3)}
            cur["regs"].append(reg)
    return blocks


def gen_md(blocks):
    out = ["# ZIRH-2 register map",
           "",
           "GENERATED from regmap.yaml by scripts/regmap_gen.py - do "
           "not edit. The YAML is the single source; the RTL decode "
           "blocks are its ground truth and the R18 access tests are "
           "the net between them.",
           ""]
    for b in blocks:
        base = b["attrs"].get("base", "?")
        out.append(f"## {b['name']} ({base})")
        out.append("")
        if "description" in b["attrs"]:
            out.append(b["attrs"]["description"])
            out.append("")
        if b["regs"]:
            out.append("| offset | register | access |")
            out.append("|---|---|---|")
            for r in b["regs"]:
                out.append(f"| {r['offset']:#04x} | {r['name']} "
                           f"| {r['access']} |")
            out.append("")
    return "\n".join(out) + "\n"


def gen_h(blocks):
    out = ["/* GENERATED from regmap.yaml by scripts/regmap_gen.py - do",
           " * not edit. Include after zirh.h or standalone. */",
           "#ifndef ZIRH_REGS_H",
           "#define ZIRH_REGS_H",
           ""]
    for b in blocks:
        if not b["regs"]:
            continue
        base = int(b["attrs"]["base"], 16)
        out.append(f"#define {b['name']}_BASE_ADDR 0x{base:08X}u")
        for r in b["regs"]:
            out.append(f"#define {b['name']}_{r['name']}_ADDR "
                       f"0x{base + r['offset']:08X}u")
        out.append("")
    out.append("#endif")
    return "\n".join(out) + "\n"


def crosscheck(blocks):
    """fw/zirh.h (hand-written) must agree on every address it names."""
    zh = (root / "fw" / "zirh.h").read_text()
    gen = {}
    for b in blocks:
        if not b["regs"]:
            continue
        base = int(b["attrs"]["base"], 16)
        for r in b["regs"]:
            gen[f"{b['name']}_{r['name']}"] = base + r["offset"]
    checks = {
        "UART_STATUS": gen.get("UART_STATUS"),
        "UART_TXDATA": gen.get("UART_TXDATA"),
        "UART_RXDATA": gen.get("UART_RXDATA"),
        "UART_BAUD":   gen.get("UART_BAUD"),
        "HK_CTRL":     gen.get("HK_CTRL"),
        "HK_CPU_SIG":  gen.get("HK_CPU_SIG"),
        "HK_INJECT":   gen.get("HK_INJECT"),
        "HK_ENV_RO":   gen.get("HK_ENV_RO"),
        "HK_ENV_SB":   gen.get("HK_ENV_SB"),
        "IFC_CAN_STAT": gen.get("IFC_CAN_STAT"),
        "IFC_CAN_CTRL": gen.get("IFC_CAN_CTRL"),
        "IFC_SPW_STAT": gen.get("IFC_SPW_STAT"),
        "IFC_SPW_CTRL": gen.get("IFC_SPW_CTRL"),
    }
    fails = 0
    for name, addr in checks.items():
        m = re.search(rf"#define {name}\s+REG32\(([A-Z_]+) \+ (0x[0-9A-Fa-f]+)\)", zh)
        if not m:
            continue
        basename = m.group(1)
        mb = re.search(rf"#define {basename}\s+(0x[0-9A-Fa-f]+)", zh)
        got = int(mb.group(1), 16) + int(m.group(2), 16)
        if got != addr:
            print(f"FAIL {name}: fw/zirh.h says {got:#x}, "
                  f"regmap says {addr:#x}")
            fails += 1
    return fails


def main():
    blocks = parse((root / "regmap.yaml").read_text())
    md = gen_md(blocks)
    h = gen_h(blocks)
    if "--check" in sys.argv:
        fails = 0
        for path, want in ((root / "docs" / "REGMAP.md", md),
                           (root / "fw" / "zirh_regs.h", h)):
            if not path.exists() or path.read_text() != want:
                print(f"FAIL drift: {path.relative_to(root)} does not "
                      "match regmap.yaml - run scripts/regmap_gen.py")
                fails += 1
        fails += crosscheck(blocks)
        nregs = sum(len(b['regs']) for b in blocks)
        print(f"regmap: {len(blocks)} blocks, {nregs} registers, "
              f"{fails} failures")
        sys.exit(1 if fails else 0)
    (root / "docs" / "REGMAP.md").write_text(md)
    (root / "fw" / "zirh_regs.h").write_text(h)
    print("generated docs/REGMAP.md and fw/zirh_regs.h")


if __name__ == "__main__":
    main()
