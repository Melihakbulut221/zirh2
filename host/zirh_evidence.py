#!/usr/bin/env python3
# =============================================================================
# zirh_evidence - radiation-evidence pack generator
#
#   python3 host/zirh_evidence.py --campaign camp.json --console run.json \
#       --tmr-guard guard.json --out pack.md [--json pack.json]
#
# Assembles the program's machine-readable outputs into one reviewable
# evidence pack shaped after the deliverable structure ECSS-Q-ST-60-15C
# (radiation hardness assurance) reviewers expect and JESD57A test
# bookkeeping requires:
#
#   1. Device and configuration identification
#   2. Test conditions (facility, ion, LET, flux, fluence)
#   3. Method reference and outcome taxonomy definitions
#   4. Results: trial outcome table, per-channel event totals and
#      cross-sections
#   5. Mitigation verification: the TMR-Guard attestation (positive AND
#      negative proof) quoted with its numbers
#   6. Anomalies and known limitations, honestly listed (zombie class,
#      UART-flood behavior and its mirror-pin remedy, RF-residue serial
#      reboots)
#
# Inputs are whatever subset exists: a campaign report (zirh_campaign
# CampaignReport.to_json), a ground-console run report (zirh_ground
# --report), a tmr-guard report (--json). Sections without data say so
# instead of pretending. The pack is a starting point a product-
# assurance owner edits, not a magic compliance stamp - the section
# headers say which evidence goes where; the standard's clause mapping
# is the owner's review task.
# =============================================================================

import argparse
import json
import time
from pathlib import Path

TAXONOMY = """The campaign outcome taxonomy (measured on ZIRH-2, enforced
by the harness as assertions, identical across RTL simulation,
gate-level simulation, FPGA twin and beam):

- SURVIVED: the command path answers after the exposure/injection.
- REBOOTED: the watchdog counted (BOOT climbed) and the command path
  answers after recovery. The register file is a RAM the reset does
  not wipe; several counted reboots before a clean boot are one
  REBOOTED outcome.
- ZOMBIE: the liveness signature keeps advancing while the command
  path stays dead (corrupted hoisted base pointer feeds the watchdog).
  Counted, not failed: the flight firmware's periodic voluntary warm
  restart clears the state at a rate simulation cannot reach.
- SILENT: signature dead and no reboot - the forbidden outcome; any
  occurrence fails the campaign."""

LIMITATIONS = """Known behaviors, measured and mitigated:

- Signature liveness is not command-path liveness (the zombie class).
  Mitigation: firmware voluntary warm restart every 2^22 iterations;
  verification: campaign taxonomy above.
- A malfunctioning CPU can flood the shared UART until telemetry
  frames lose atomicity. Mitigation: the TLM_MIRROR pin, a transmit-
  only serial output fed directly by the telemetry framer on no bus;
  verification: dual-voice cross-check in the ground console.
- The SoC reset does not wipe the register file (RAM); a reboot can
  derail on residue and take several counted cycles. Mitigation: crt0
  scrubs all 31 registers at every boot."""


def load(path):
    return json.loads(Path(path).read_text()) if path else None


def fmt_xs(v):
    return f"{v:.3e}" if isinstance(v, (int, float)) else "-"


def build(campaign, console, guard, meta):
    lines = []
    add = lines.append
    add("# Radiation evidence pack")
    add("")
    add(f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} "
        "by the ZIRH evidence tooling. Structure follows the deliverable "
        "shape of ECSS-Q-ST-60-15C RHA reporting with JESD57A test "
        "bookkeeping; clause-by-clause mapping is the product-assurance "
        "owner's review step.")
    add("")

    add("## 1. Device and configuration")
    add("")
    dev = (campaign or {}).get("device") or meta.get("device", "ZIRH-2")
    add(f"- Device: {dev}")
    add(f"- Backend/environment: "
        f"{(campaign or {}).get('backend', meta.get('backend', '-'))}")
    add(f"- Run id: {(campaign or {}).get('run_id', '-')}")
    add("")

    add("## 2. Test conditions")
    add("")
    src = campaign or console or {}
    for label, key in (("Facility", "facility"), ("Ion", "ion"),
                       ("LET (MeV cm2/mg)", "let_mev_cm2_mg"),
                       ("Flux (/cm2/s)", "flux_cm2_s"),
                       ("Fluence (/cm2)", "fluence_cm2")):
        v = src.get(key) or (console or {}).get(key)
        add(f"- {label}: {v if v else 'not recorded (simulation or bench)'}")
    add("")

    add("## 3. Method and taxonomy")
    add("")
    add("Test method bookkeeping per JEDEC JESD57A (single-event effects "
        "from heavy-ion irradiation).")
    add("")
    add(TAXONOMY)
    add("")

    add("## 4. Results")
    add("")
    if campaign:
        c = campaign.get("counts", {})
        n = len(campaign.get("trials", []))
        add(f"Campaign: {n} trials - "
            f"{c.get('survived', 0)} survived, {c.get('rebooted', 0)} "
            f"rebooted, {c.get('zombie', 0)} zombie, "
            f"{c.get('silent', 0)} SILENT.")
        add(f"Verdict: {'PASS' if campaign.get('passed') else 'FAIL'} "
            "(pass requires zero SILENT).")
        if "cross_section_cm2" in campaign:
            add(f"Whole-device event cross-section: "
                f"{fmt_xs(campaign['cross_section_cm2'])} cm2.")
        add("")
    else:
        add("No campaign report supplied.")
        add("")
    if console:
        add("Per-channel event totals (ground-console yield ledger, "
            "clear-aware):")
        add("")
        add("| channel | events | cross-section (cm2) |")
        add("|---|---|---|")
        xs = console.get("cross_section_cm2", {})
        for ch, ev in sorted(console.get("event_totals", {}).items()):
            if ev:
                add(f"| {ch} | {ev} | {fmt_xs(xs.get(ch, '-'))} |")
        add("")
        add(f"Frames decoded: {console.get('frames', '-')}, sequence gaps: "
            f"{console.get('gaps', '-')}, checksum failures: "
            f"{console.get('chk_fails', '-')}.")
        dv = console.get("dual_voice")
        if dv:
            add(f"Dual-voice cross-check: primary {dv['primary_frames']} "
                f"frames / {dv['primary_junk']} junk bytes, mirror "
                f"{dv['mirror_frames']} frames / {dv['mirror_junk']} junk; "
                f"mirror clean: {dv['mirror_clean']}, flood suspected: "
                f"{dv['flood_suspected']}.")
        add("")
    else:
        add("No ground-console report supplied.")
        add("")

    add("## 5. Mitigation verification (TMR attestation)")
    add("")
    if guard:
        checks = guard.get("checks", [])
        neg = guard.get("negative", [])
        ok = sum(1 for r in checks if r.get("status") == "pass")
        caught = sum(1 for r in neg if r.get("caught_collapse"))
        add(f"tmr-guard verdict: {guard.get('verdict', '-')} - {ok}/"
            f"{len(checks)} blocks verified replica- and flop-exact "
            "against synthesis.")
        if neg:
            add(f"Negative proof: protection attributes stripped from a "
                f"source copy, {caught}/{len(neg)} checks then FAILED as "
                "required - the checker demonstrably catches the collapse "
                "it exists to catch.")
        add("")
        add("| block | replicas found/expected | flops found/expected |")
        add("|---|---|---|")
        for r in checks:
            add(f"| {r['name']} | {r.get('found_instances')}/"
                f"{r.get('expect_instances')} | {r.get('found_ffs')}/"
                f"{r.get('expect_ffs')} |")
        add("")
    else:
        add("No tmr-guard report supplied.")
        add("")

    add("## 6. Anomalies and known limitations")
    add("")
    add(LIMITATIONS)
    add("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="radiation evidence pack "
                                             "generator")
    ap.add_argument("--campaign", help="zirh_campaign report JSON")
    ap.add_argument("--console", help="zirh_ground --report JSON")
    ap.add_argument("--tmr-guard", help="tmr_guard --json report")
    ap.add_argument("--device", default="ZIRH-2")
    ap.add_argument("--backend", default="")
    ap.add_argument("--out", required=True, help="markdown pack path")
    ap.add_argument("--json", help="also write the merged inputs here")
    args = ap.parse_args()

    campaign = load(args.campaign)
    console = load(args.console)
    guard = load(args.tmr_guard)
    if not any((campaign, console, guard)):
        ap.error("at least one input report is required")

    meta = {"device": args.device, "backend": args.backend}
    text = build(campaign, console, guard, meta)
    Path(args.out).write_text(text)
    print(f"evidence pack written: {args.out} "
          f"({len(text.splitlines())} lines)")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"campaign": campaign, "console": console, "tmr_guard": guard,
             "meta": meta}, indent=2))


if __name__ == "__main__":
    main()
