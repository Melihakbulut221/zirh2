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

## Cycle 10 (2026-08-13): the pre-beam prediction campaign

The systematic gate-level SEU sweep is in the gl_test job and green on
the shipped netlist: 384 exhaustive singles (every replica flop of both
chains, both pattern phases) landed as exactly one RAW count each with
ZERO escapes; the 192 cross-replica pairs mapped the escape window to
same-bit-same-cycle and nothing else - simultaneous same-bit pairs
escape exactly once each, staggered and split-bit pairs never.
scripts/seu_predict.py folds the final-DEF distances over the escape
window: chain B's closest same-bit pair is 3.78 um (35 pairs under
5 um), chain A's macro floor is 680 um - so the beam escape ratio
measures spatial double-upset probability and nothing else.
docs/PREDICTION.md registers the falsifiable pre-beam claim,
docs/PAPER.md is the manuscript draft around it (RADECS/NSREC track).
Also closed on the way: twin-lite (4612/5280 LC, 87%, bitstream green),
the twin ROM ack-timing bug, and the local GL recipe hardened against
reboots (TT iverilog v13 permanent in ~/.local/opt - vanilla v12 reads
the whole die X, the day's most expensive lesson).

## Decision (2026-08-13): FPGA twin program retired

The open twin-board question is resolved: no board. The UP5K fit
history and the lite configuration stay documented in fpga/README.md;
the fpga workflow is removed; the SYNTH/TWIN guards stay dormant in
the RTL. Beam rehearsal is the gate-level campaign, which the SEU
sweep proves on every hardening run.

## Cycle 11 (2026-08-13): the verification deepening

Three legs, all green, all rootless:

1. FORMAL. The escape-window theorem is proven, not sampled:
   formal/f_ring.sv + scripts/formal.sh (yosys-smtbmc, z3, BMC plus
   unbounded k-induction at N = 4, 8 and the shipping 32) - under an
   arbitrary infinite upset stream confined to one replica per cycle,
   the voted output equals the golden ring in every bit of every
   cycle. The dual cover property makes the solver construct the
   escape itself; its GTKWave render is docs/fig/escape_witness.png
   and Fig. 1 of the manuscript.

2. TORTURE. scripts/torture_gen.py + scripts/torture.sh: random RV32I
   programs sized for the 256-word ROM (ALU, shifts, forward skips,
   ECC-RAM loads/stores) against an independent golden model, digest
   judged at the UART pins through the exact integration we modified
   by hand - the pipelined fetch, the ROM dbus port, the bus mux, the
   ECC RAM. 100/100 programs match. Debugging the harness caught a
   generator bug (the digest chain xor-ing through its own
   accumulator), not an RTL bug - the RTL survived its accuser.

3. ECC SECDED, proven. formal/f_ecc.sv against the shipped encode and
   decode (a FORMAL-only fault port XORs the read view; zero silicon):
   roundtrip, single-bit correction at every one of the 39 stored
   positions, two-bit detection with an empty miscorrection space, and
   the read-correct-merge-reencode partial-write path never laundering
   a corrupted byte - exhaustive over all words, faults and initial
   states, 39 seconds of z3. A deliberately mutated decode fails the
   proof immediately, so it has teeth. Both formal legs and a 30-
   program daily-seed torture now run on every push (formal.yaml).

4. The methodology borrows the riscv-dv/core-v-verif idea without
   their UVM machinery (tied to commercial simulators and other
   cores); OpenTitan's flow was evaluated and skipped as
   infrastructure-bound. GTKWave runs rootless from an extracted deb
   with Xvfb for headless rendering.

## Cycle 12 (2026-08-14): the memory workstream lands - scrubber,
## address mask, and the ghost that taught the slicing discipline

zirh_sram39 now carries the full A3/A4 stack, green on the 1024-word
suite: registered-decision background scrubber (a divider-paced sweep
through the same read-correct-writeback path, TMR counter and address
walk, scrub_en gate for the boot-init window), and the address-in-ECC
mask (even-weight fold of the row over the parity positions and the
overall bit). Two formal results anchor it: the SECDED contract
re-proven over the shared include after the refactor, and a new proof
that a wrong-row read - every single-bit address flip - decodes
UNCORRECTABLE for all 2^32 words and all row pairs with differing
folds: wrong-row data can never come back "clean" or "corrected".

The build fought two real bugs worth recording. First, the original
scrubber muxed the macro address combinationally between the bus and
the scrub counter; a bus request landing inside a scrub cycle steered
repair writes to the wrong row. Fix: every macro control signal now
derives from registered state. Second, a mechanical edit that
switched the slices' address port from the bus index to the arbitrated
row matched four instances and silently missed the fifth (its
destructured port list differed by one character), leaving the parity
slice on the live bus address: bus reads stayed accidentally coherent
while every scrub beat read parity garbage, "repaired" phantom errors
and slowly shredded the array. The hunt closed by reading the phantom
syndrome sequence as a chain - each beat's parity byte was exactly
the previous repair's write-through - which pointed at the one
instance whose address had never moved. The lesson is now discipline:
slice instantiations are generate-loops or nothing, and every
mechanical multi-site edit gets a grep count against the expected
site count before it gets a simulation.

## Cycle 13 (2026-08-14): the boot architecture lands

docs/BOOT.md is the contract - the mask ROM becomes an immutable
loader plus golden firmware, application images live in external
rad-tolerant NVM or arrive from the host, execute from the SECDED
SRAM - and zirh_boot_ctrl.v is its first hardware: transport-agnostic
byte-stream sink, SRAM bus master, TMR state with the safe-state trap
landing on GOLDEN (a mangled loader fails toward the mask ROM, never
toward silence). The suite proves the claims on the real SECDED SRAM:
a bank's valid flag flips only after the STORED image's read-back CRC
matches (interruption tolerance is structural - a half-written bank
never looks bootable), rejects fall back other-bank-then-golden, the
HOST-mode ISP path stages fresh images into the inactive bank while
running, and the watchdog revert ladder walks bank to bank to golden
with no ground contact. The signature hook (sig_ok_i) is in the FSM
so the product chip's public-key verdict drops in without touching
the flow.
