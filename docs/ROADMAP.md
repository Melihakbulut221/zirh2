# ZIRH program roadmap - profitability x engineering, 2026-08-09

Two independent analyses - one from the commercial side (who pays, for
what, via which mechanism) and one from the systems-engineering side
(what fits, what it builds on, what it costs) - converged on the same
short list. This document is their intersection and the standing
execution loop that works through it. The die is frozen at 83.3%; every
DO-NOW item is software, firmware, test, or flow work.

## The loop

Each cycle: take the top OPEN item, build it, test it, push it, record
the outcome here, re-rank what remains. Findings from any cycle feed
back into the ranking. Silicon items accumulate in the ZIRH-3 section
until a shuttle decision opens a die budget.

## DO-NOW queue

| # | Item | Why (commercial x engineering) | Effort | Status |
|---|------|-------------------------------|--------|--------|
| 1 | crt0 register-file scrub | Closes the measured RF-residue reboot hole; must land before the GL campaign baselines firmware-dependent counts | S | DONE (cycle 1) |
| 2 | TMR-Guard: manifest-driven check_tmr CLI | Sharpest commercial pain (synthesis silently deletes TMR; no independent verifier exists on the market), smallest effort - the methodology and the negative test are already written | S | DONE (cycle 2) |
| 3 | GL fault campaign on the routed netlist | The survived/rebooted/zombie contract has never run on the netlist that will fly; highest chance of a real find before submission | M | DONE (cycle 3) |
| 4 | Campaign orchestration library | One classifier and injection DSL for RTL, GL, twin and beam backends; this IS the qual-pipeline product seed, and the zombie taxonomy is its unfair advantage | M | DONE (cycle 4) |
| 5 | Ground console: fluence + cross-section + dual-port decode | At ~USD 3k/hour beam rates, live yield accounting pays for itself in one shift; the mirror stream cross-check is built but software never exploits it | M | DONE (cycle 5) |
| 6 | STA corner/skew/perturbation sweep | Closes SCOPE's cross-macro skew open item; proves the +27 ps fast-corner hold is the recipe, not luck | S-M | DONE (cycle 6) - sweep dispatched |
| 7 | FPGA twin bitstream + soak | The ECC-RAM BRAM-mapping question and the never-executed 2^22 warm restart only die on hardware; doubles as the eval-kit credibility asset | M | MEASURED (cycle 7) - board decision open |
| 8 | ECSS evidence-pack templates | Converts items 4+5 outputs into ECSS-Q-ST-60-15C Rev.1 deliverable structure - the tender-blocking tier | M | DONE (cycle 8) |

## ZIRH-3 silicon backlog (ranked)

1. SET pulse-width Vernier TDC - direct upgrade of a flying instrument;
   sized by ZIRH-2 beam event rates.
2. SpaceWire time-codes (ECSS-E-ST-50-12C) - zero new pins, the
   time-code FSM is one more trap-encoded beam target.
3. Clock-loss observer (RO-clocked watchdog) - the SEFI a synchronous
   die cannot see; RO mechanics already proven.
4. SRAM DUT - gated on sg13g2 SRAM macro availability in the flow.
5. CAN 2.0B per ECSS-E-ST-50-15C - NOT CAN FD (no ECSS standardization;
   an FD core is a science-free area sink).
6. Region-gated clock hold-and-heal A/B - only after ZIRH-2 beam
   ESCAPE/heal data, per the recorded gate.

## Product track (rides on beam credibility)

- SG13G2 hardened-macro kit: zirh_tmr_lib + keep_hierarchy discipline +
  check_tmr methodology + macro hardening workflow + the run-13
  placement recipe as documented flow defaults.
- Safe-state TMR FSM generator - LANDED (cycle 9):
  scripts/tmr_fsm_gen.py emits the CAN/SpW pattern from a JSON spec
  (states, recovery state, priority-ordered transitions): voted-feedback
  TMR state register, case-default trap to the recovery state, and -
  the point - the tmr-guard manifest entry with replica and flop counts
  COMPUTED (width x 3 + 1 err flop; power-of-two state counts widen one
  bit so a trap always exists). Closed-loop proven: a generated 5-state
  FSM verified by tmr-guard at exactly the predicted 3 replicas / 10
  flops, stripped copy correctly failing.
- TMR interface IP mini-library (CAN/SpW/RS-422 cores with golden
  models and attestations; Gaisler-style per-project licensing).
- Radiation-canary soft macro (TID RO + SET catcher + burst correlator
  as drop-in RTL).
- The ESCAPE(A/B) beam dataset: the price of placement separation in
  one number - nobody has it for an open 130 nm flow; the credibility
  engine for everything above.

## Cycle log

- CYCLE 1 (2026-08-09): crt0 RF scrub LANDED - 31 boot-time writes,
  checksum 0xF4 (227/256 ROM words used), firmware-dependent counts
  unmoved (soc 2160 / top 3690), soc 3/3, integration 6/6, z2 3/3
  against the scrubbed mask.
- CYCLE 2 (2026-08-09): TMR-Guard LANDED - scripts/tmr_guard.py, a
  manifest-driven independent TMR synthesis-survival verifier with
  machine-readable reports and a --prove-checker mode that strips the
  protection attribute from a source copy and requires every check to
  FAIL there. Self-test on this design: 7/7 positive, 7/7 negative.
  Both field-measured counting gotchas (per-definition selection,
  post-techmap DFF summing) are handled in the tool, not in comments.
- CYCLE 3 (2026-08-09): GL fault campaign LANDED - test_gl_campaign.py
  runs inside the existing gl_test CI job (GATES=yes appends the
  module; RTL runs skip it). Targets come from the netlist itself:
  3594 DFFs = 1174 keep_hierarchy-island flops with readable prefixes
  + 2420 anonymous core flops whose hierarchy dissolved at synthesis;
  injection is Force/Release on Q nets resolved through one VPI pass
  (dotted island names break path lookup - measured). Local replica
  run on the shipped netlist: six as-placed single-replica flips, six
  ERR_TMR pulses, CPU alive after. Enabling local GL took three
  measured fixes now in the repo: unpowered nl (not pnl), the ciel
  PINNED cell models, and TinyTapeout's patched iverilog v13 (vanilla
  icarus leaves the models' $setuphold delayed nets undriven and the
  whole die reads X - proven on a single cell).

## VERIFICATION CLOSED (2026-08-12): the nine-cycle RTL is green

After the multi-day placement/routing fight, gds+precheck+gl_test+viewer
all pass on the full nine-cycle design (commit with the ibus-fetch
pipeline). Final: utilization 83.3%, setup +22.0 ns, hold clean every
corner (+26 ps fast, +165 ps typ, +405 ps slow, zero violations),
DRC/LVS/antenna zero. The GL fault campaign ran in CI for the FIRST
time - test_gl_campaign 8/8 in gl_test, so the survived/rebooted/zombie
contract is now proven on the netlist that flies, not just RTL.

Root cause of the routing crisis, for the record: the boot RF-scrub
mask filled ROM words the pre-scrub mask left zero, denying synthesis
the constant-folding that kept the flat 256x32 combinational fetch mux
routable; four six-hour runs plateaued at ~5k shorts and three
placement configs proved it structural, not a placement draw. Fix:
register only the instruction-fetch read port (yosys merges it into a
synchronous memory read, MEMORY_DFF, dissolving the comb cone),
dbus left combinational so the command path is byte-identical. All
software cycles plus the ASIC verification are now complete; the open
items are the twin board decision and ZIRH-3 silicon.
