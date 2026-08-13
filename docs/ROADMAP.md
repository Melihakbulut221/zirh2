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

## Cycle 14 (2026-08-14): debug lock and the DFT plan

docs/DEBUG-DFT.md registers F27/F28: the riscv-dbg + JTAG stack plan
with the two rad-hard requirements a stock module lacks, and the DFT
ladder (scan with voter-bypass and a tmr-guard scan check, the march/
BIST engine over the macros' A_BIST ports serving production,
flight self-test and the A6 beam experiment at once, IDDQ and
screening modes, BSDL). The buildable piece is built: zirh_dbg_gate
is the isolation boundary itself - the strap latches ONCE at POR
(product: fuse), there is no software unlock because a register that
can unlock is a register an upset can flip, every debug-to-system
signal is AND-masked (a mux select upset could pass a live value; an
AND with a voted zero is dead), and the TMR trap fails toward
LOCKED. The suite hammers a locked gate with random debug garbage
and sees zero leakage; the formal harness proves by induction that
the verdict is absorbing - locked stays locked, open stays open,
strap wiggling and upsets notwithstanding - and the cover shows the
bench path exists. Brief v2 is registered verbatim in PROGRAM.md:
the MRAM SiP architecture with capacity floors, the G test ladder
(30-39) and the H repo-hygiene contract (40-49) are now the queue.

## Cycle 15 (2026-08-14): the march/BIST engine - one block, three
## customers

zirh_sram_bist drives the A_BIST port set the RM_IHPSG13 macros ship
with (the functional port is muxed away by construction, so BIST is
exclusive without any glue): MARCH C- over all five slices in
parallel for production screening and commanded flight self-test, and
checkerboard fill + read-only scan as the A6 beam pattern-scan front
end. The scan REPORTS and never repairs - a repair would erase the
event the beam experiment exists to count - and the suite proves
exactly that: a disturbed row is detected at the right address with
the right slice map, a second scan still sees it, and a subsequent
march rescreens the array clean. All engine state is TMR with the
trap landing on IDLE (a mangled test engine must never keep
scribbling). The Cycle-12 lesson became structure on the way: the
five slice instantiations are now ONE generate loop - identical
wiring by construction, no fifth instance for a mechanical edit to
miss.

## Cycle 16 (2026-08-14): the CI line closes the biggest gap

H41 said it plainly: in a one-person project, CI is the first answer
to the self-verifying-single-person objection. ci.yaml now runs on
every push what previously ran only on this bench: the verilator lint
gate (which caught a REAL mixed blocking/nonblocking assignment in
the SpaceWire encoder's parity register on its very first pass - the
gate justified itself before it was even committed), all six unit
suites (housekeeping, SECDED SRAM, boot controller, BIST engine,
debug gate, bare macro smoke) against the ciel-pinned PDK, and the
tmr-guard synthesis-integrity check that proves the optimizer did not
silently collapse the TMR. Waivers are few and each carries its
reason in scripts/lint.sh; LATCH, WIDTHTRUNC and BLKANDNBLK stay
armed. README wears the badges. Full container-image pinning is the
registered follow-up; versions are pinned at pip/ciel level and
echoed into every log today.

## Cycle 17 (2026-08-14): traceability as code and the repro handle

H49 and H43 land together because they are the same promise from two
sides: every claim has a test, and every test replays. requirements
.yaml maps nineteen requirements - from the escape-window theorem to
the no-brick boot property to every historic unit suite - onto their
thirty-eight test files and the CI jobs where the evidence runs;
scripts/trace_check.py enforces the chain on every push (a
requirement without an existing test fails the build, a test no
requirement claims is reported before the map can drift). The gate's
first run listed twenty-one orphan suites - the whole pre-program
test family - and the map grew five requirements on the spot to claim
them: the matrix now covers the repository, not just the new work.
The root Makefile is the single entry point: units, lint, formal,
tmr, trace, and make repro SEED=x, which replays any recorded torture
seed to bit-identical verdicts; test/seeds.txt records every seed
this project has used and what it proved. CI runs the same entry
points; green here means green there.

## Cycle 18 (2026-08-14): the frozen analysis and the codified glance

H48: scripts/beam_analysis.py is the registered analysis - exact
Poisson rate-ratio inference for ESC(B)/ESC(A) with fluence
normalization (the G37 statistics design executed), the TT-harness
confound subtraction with propagated uncertainty (G36), and the
Weibull cross-section-vs-LET fit, all standard-library-only so the
frozen script runs anywhere, forever. Its selftest runs in CI on
every push against synthetic truth: the 10x-elevated case must flag,
identical rates must not, a pure-harness run must come back
insignificant, and the fit must recover a known curve. When beam data
arrives the script runs untouched - the prediction discipline
extended to the analysis.

H40: the waveform policy is code now - raw dumps never commit
(.gitignore enforces it), test/waves/ carries the .gtkw save files
that codify where to look in every major testbench, docs/fig/ holds
the annotated evidence figures, and curated mini-dumps have a stated
home and size budget.

## Cycle 19 (2026-08-14): the register map as data, the bench as code

H47: regmap.yaml is the single machine-readable source of the
register map, transcribed from the RTL decode blocks - every UART,
housekeeping, environment and interface register with its fields,
one-shot semantics and reset notes. scripts/regmap_gen.py generates
docs/REGMAP.md and fw/zirh_regs.h from it, and the CI sync gate
regenerates and diffs on every push: the YAML, the doc and the header
cannot drift apart silently, and the hand-written fw/zirh.h is
cross-checked address by address (it agreed on all thirteen - the
firmware and the RTL were already telling the same story, and now a
gate keeps it that way).

H45: host/zirh_bench.py is the G31 bring-up ladder as code - smoke
(frames, checksums, sequence, living signature, echo, exit code for a
rig), soak (the long logger with the false-positive-floor report that
certifies the beam counters), and shmoo (envelope mapping with a
pluggable instrument interface that degrades to operator prompts).
All of it tested today against a mock of the chip's telemetry in CI:
the smoke must pass on the healthy mock, must catch a broken
sequence, and the quiet soak floor must be exactly zero. Silicon day
is a key press. The traceability map grew R20 and R21 to claim both.

## Cycle 20 (2026-08-15): coverage, single-source assertions and the
## ISA verdict

The last three hygiene items land. H44: zirh_assert.vh states each
module's self-invariants once - simulation compiles them into fatal
checks so every suite polices them continuously, formal compiles the
same text into proof obligations, and the ASIC build compiles them
into nothing. H42: the FSM coverage gate demands every expected arc
of the four product-program FSMs was seen (26/26, with POR arcs a
classified legality, and unmapped arcs failing the build so the map
tracks the RTL). H46: the integrated serv_rf_top passes the full
riscv-arch-test rv32i suite - 38 of 38 signatures identical to the
shipped 2.7.4 references - through a harness that survived three
honest fights: branch-test images overflowing 128 KB, the jal jump
matrix demanding 2 MB, and modern binutils rejecting the suite's
la-x0 idiom, solved by patching the PREPROCESSED text with an
equal-size x0-write pair so layout and semantics both hold. The
toolchain is the same pinned xpack gcc the firmware builds with;
arch.yaml runs the suite in CI on every push.

## Cycle 21 (2026-08-15): the campaign paperwork, finished before the
## application

docs/BEAM-PLAN.md executes the brief's rule that campaign design
finishes before any facility application: protons first (TAEK/SANAEM
Ankara flagged as the local option to investigate), neutrons for
cheap statistics, heavy ions for the LET curve with decapsulation
budgeted; the statistics designed up front (30-50 events per chain,
flux capped at one event per readout window, the console re-planning
from the first measured hour); the TT-harness confound protocol
registered in writing with its control run, attribution rules and
recovery ladder; ESCC 25100/JESD57 reporting shape; and the honest
checklist showing exactly which boxes are engineering (done) and
which are the owner's gates (silicon, money, the DUT board build).
docs/TID-SEL-PLAN.md does the same for the other two campaigns: the
TM1019-shaped stepped-dose flow that also calibrates the on-chip RO
dosimeter into an absolute instrument, and the worst-case SEL
experiment with its current-signature machinery - sequenced so TID
runs first on cheaper irradiator time and SEL rides the ion shift's
final hot run.

## Cycle 22 (2026-08-15): the MRAM leg - the A5 chain closes in
## simulation

zirh_qspi is the chip-side piece of the persistent-memory
architecture: SPI mode 0, standard READ on one lane and quad-output
READ with dummy cycles on four, the byte stream landing directly on
the boot controller's transport-agnostic port. Flow control belongs
to the consumer - a stalled stream freezes SCK with CS held, and the
transfer resumes without losing a bit (proven under seventy percent
random backpressure). Abort and the TMR trap both release the bus
immediately: a mangled controller must let go, never hold the MRAM
hostage. The crown of the suite is the whole A5 chain in one test: a
firmware image in behavioral MRAM, streamed by the controller,
CRC-verified on stored data by the boot controller, committed into
the five-macro SECDED SRAM, boot_sel flipped - the architecture the
product will fly, green in simulation before any board exists.

## Cycle 23 (2026-08-15): the watchman who does not sleep

zirh_clkobs is the C11 item the brief said to pull forward: the
external clock is a failure the die cannot see from inside its own
domain, because every flop that could report the death dies with it.
The observer lives on an independent ring-oscillator clock and
watches the main domain's heartbeat from outside - a two-flop
synchronizer, an idle counter that declares loss, a recovery counter
that restores the level, a sticky event and a survivor count for
telemetry, all TMR on the observer clock. The suite hand-drives the
main clock precisely so it can genuinely kill it - a cocotb Clock
cannot die - and asserts detection, recovery, sticky semantics and
the second death counted. The ASIC ring binds with the zirh_env_ro
hand-instantiated cell discipline at the product-chip step; the
module deliberately carries no main-clock assertions, because the
main clock is the thing that dies.

## Cycle 24 (2026-08-15): the DUT board on paper, testable before it
## exists

docs/DUT-BOARD.md closes the last engineering box on the beam
checklist: a build-ready specification where every requirement cites
the campaign document that demanded it. The SEL machinery is
autonomous hardware - comparator trip under ten microseconds into a
p-FET rail switch, because a latched DUT cooking during a network
hiccup is how campaigns lose their silicon - with thresholds derived
from measured bench baselines, never guessed. The mirror channel
gets its own driver, cable and adapter, sharing nothing with the
primary voice it exists to outlive. The mechanics keep everything
but the carrier out of the spot so the G36 confound stays confined
to what the control run measures, and the riser flips for the laser
TPA session without redesign. The bring-up plan makes the board
provable before any facility: trip rehearsal on an electronic load,
long-cable soak, and a full remote-only mock shift with the door
shut - if anything needs a hand, fix the board, not the procedure.

## Cycle 25 (2026-08-15): tmr-guard becomes a product

E19 executed to its smallest-effort-first-revenue shape. The tool
moves to its own home with a vendor-neutral thirty-line demo whose
manifest numbers were measured, not declared - the tool's own
philosophy applied to its own demo - and whose negative control IS
the sales pitch: one command passes, the next strips the attributes
and proves the checker catches the collapse it exists for. The
flagship example is ZIRH-2's own ten-block manifest, and both now
run in CI on every push, so the product demos itself continuously.
The one-pager sets the delivery ladder - open core now, support
engagements as first revenue, the standalone split when an external
user exists and not before - and leaves outreach, licensing and the
split decision at the owner's gate where they belong.

## Cycle 26 (2026-08-15): corner timing and X-propagation, closed green

G30's flow is built: the shipped netlist simulates with the hardening
run's OWN SDF at the three characterized corners including both
military-range extremes, through a plusarg annotation shim that
touches nothing else, with the X-propagation pin monitor armed in
the same test - after boot, an unknown reaching any output pin fails
the run. The support question was settled by a two-gate
micro-experiment before trusting anything: the TT iverilog's
sdf_annotate silently ignores min::max pairs WITHOUT a typical value
and applies full triples correctly - and the OpenROAD SDF emits full
triples, so the flow is sound; the lesson (an annotator that returns
success is not an annotator that annotated - verify with a delay you
can see) is now recorded. sdf.yaml runs the three-corner matrix on
demand per hardening release, staging netlist and SDF from the SAME
named run, never mixed.

FOLLOW-UP, all three corners run locally to completion: slow
(nom_slow, 1.08 V, 125 C - the binding setup corner), typical
(nom_typ, 1.20 V, 25 C) and fast (nom_fast, 1.32 V, -40 C - the
hold-risk extreme) each boot the shipped netlist at its own real
delays, produce a valid telemetry frame from a living CPU, and
finish with ZERO unknowns reaching any output pin after the monitor
arms. TESTS=1 PASS=1 at every corner. The pre-silicon timing gap
G30 named is closed: the netlist keeps its word across the full
military range in both directions, and the X-propagation monitor -
the part a pure STA report cannot give - confirms no un-initialized
state ever leaks to a pin. The same three-corner matrix stays
repeatable against any future hardening release via sdf.yaml.

## Cycle 27 (2026-08-15): the software ecosystem's first stone

F29 starts where the competition's real value lives: fw/hal/ is the
driver layer - UART, watchdog signon, the full EDAC counter block,
fault injection, the environment instruments and both interface
experiments - written as static inline over the GENERATED register
header, so the HAL cannot drift from the RTL without the CI regmap
gate failing first. The example application is the canonical
flight-shaped main loop (sign on, watch the counters, make
uncorrectables loud, answer the ground) and compiles to 244 bytes at
-Wall -Werror with no libc; the linker script places a loaded
application in the boot controller's bank layout per docs/BOOT.md.
The fw workflow gates the compile on every push. Toolchain, linker
scripts, HAL, example: four of the brief's five ecosystem items in
the repository; the dev board rides with the DUT board, and the RTOS
port stays queued for the product core.

## Cycle 28 (2026-08-15): three studies, one program-shaping finding

Three decision-support documents land, and the middle one moves a
program assumption. docs/CORE-STUDY.md picks the product core by hard
criteria (Hazard3 primary, picorv32 fallback, Ibex watched) with the
numbers to be re-measured on our own flow. docs/EXPORT-CONTROL.md is
the counsel memo: the Wassenaar/EAR rad-hard thresholds, the argument
that a measured rad-TOLERANT part sits below them, and the finding
that this program's measure-before-believing habit is accidentally an
export-compliance posture. And docs/MPW-COST.md turned up the
surprise: IHP grants roughly two square millimetres of FREE SG13G2
silicon to open-source, DRC-clean, open-tool submissions - which is
this repository exactly - so the ZIRH-3 dedicated-design rehearsal
(pad ring, guard rings, POR, SRAM macros, the whole obstacle-2 list)
waits behind the data-discipline gate, not the money gate. The
sellable part keeps its paid EUROPRACTICE path clean.
