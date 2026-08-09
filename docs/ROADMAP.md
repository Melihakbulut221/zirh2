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
| 1 | crt0 register-file scrub | Closes the measured RF-residue reboot hole; must land before the GL campaign baselines firmware-dependent counts | S | IN CYCLE 1 |
| 2 | TMR-Guard: manifest-driven check_tmr CLI | Sharpest commercial pain (synthesis silently deletes TMR; no independent verifier exists on the market), smallest effort - the methodology and the negative test are already written | S | OPEN |
| 3 | GL fault campaign on the routed netlist | The survived/rebooted/zombie contract has never run on the netlist that will fly; highest chance of a real find before submission | M | OPEN |
| 4 | Campaign orchestration library | One classifier and injection DSL for RTL, GL, twin and beam backends; this IS the qual-pipeline product seed, and the zombie taxonomy is its unfair advantage | M | OPEN |
| 5 | Ground console: fluence + cross-section + dual-port decode | At ~USD 3k/hour beam rates, live yield accounting pays for itself in one shift; the mirror stream cross-check is built but software never exploits it | M | OPEN |
| 6 | STA corner/skew/seed sweep | Closes SCOPE's cross-macro skew open item; proves the +27 ps fast-corner hold is the recipe, not luck | S-M | OPEN |
| 7 | FPGA twin bitstream + soak | The ECC-RAM BRAM-mapping question and the never-executed 2^22 warm restart only die on hardware; doubles as the eval-kit credibility asset | M | OPEN |
| 8 | ECSS evidence-pack templates | Converts items 4+5 outputs into ECSS-Q-ST-60-15C Rev.1 deliverable structure - the tender-blocking tier | M | OPEN |

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
- Safe-state TMR FSM generator (emits the CAN/SpW pattern plus its own
  check gates - retires the per-definition counting gotcha as a human
  error class).
- TMR interface IP mini-library (CAN/SpW/RS-422 cores with golden
  models and attestations; Gaisler-style per-project licensing).
- Radiation-canary soft macro (TID RO + SET catcher + burst correlator
  as drop-in RTL).
- The ESCAPE(A/B) beam dataset: the price of placement separation in
  one number - nobody has it for an open 130 nm flow; the credibility
  engine for everything above.

## Cycle log

- CYCLE 1 (2026-08-09): crt0 RF scrub - firmware change, full
  re-baseline chain (rom_init, checksum, firmware-dependent counts, GL).
