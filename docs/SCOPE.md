# ZIRH-2 scope draft

Status: draft for discussion. Nothing here is committed until ZIRH-1
silicon data exists; the decision gates below say which parts wait for it.

## Mission shift

ZIRH-1 answers a storage question: what are the SEU rates of plain versus
TMR flip-flops on this PDK, and how often is TMR defeated. ZIRH-2 answers a
system question: **does a hardened computing element keep executing under
beam, and which of its protections actually earn their area.** The chip
runs firmware continuously and its telemetry proves, frame by frame, that
it is still running it correctly.

## The headline experiment: placement A/B

ZIRH-1's known gap is that TMR replicas are placed with no separation
constraint, so one particle can defeat the voter; its ESCAPE counter
measures how often. ZIRH-2 turns that gap into the experiment:

- Chain A: TMR ring, placement-constrained (replicas forcibly separated)
- Chain B: identical TMR ring, tool-placed (the ZIRH-1 situation)
- Same die, same beam: ESCAPE(A) versus ESCAPE(B) is a direct measurement
  of what placement separation buys, in one number

This is the single highest-value addition and it reuses zirh_seu_mon
almost unchanged. It is also the riskiest flow work (see risks).

## Area reality

Numbers that gate everything (measured on ZIRH-1, not estimated):

- 4x2 tile, 60% target density: ~156k um2 usable; ZIRH-1 uses 158k (61%)
- One sg13g2 flop: ~49 um2. TMR bit: ~3.3x a plain bit after voter
- Rule burned into this project: combinational cost of TMR (voters,
  comparison trees) roughly doubles flop-only estimates. Estimate nothing;
  synthesize early and measure

Consequence: **ZIRH-2 targets an 8x2 tile** (2x the area, ~312k um2
usable at 60%). Even so, a DFF-based RAM is a trap: 256 bytes of
DFF RAM is ~2048 flops = ~100k um2 before ECC - a third of the whole
budget. RAM sizing is therefore a P0 design decision, not a detail.

## Block list

BINDING PROBE (2026-08-07): the A/B experiment is physically real.
tt_um_hma_zirh2 hardened with chain A bound to three hardened
zirh_tmr_ff64 macros (113.75 x 132.47 um each), all three FIXED at
their requested coordinates to 0.00 um: pairwise 700/680/1380 um
against the 3.8-12 um tool-placed clustering, with chain B tool-placed
on the same die as the control. Final: 81.2% utilization (high but it
closed), setup +6.48 ns, hold +0.079 ns, DRC/LVS/antenna 0, flop
accounting exact (3021 top + 3x64 in macros). PIN MAP FROZEN + DRAFT MANIFEST (2026-08-07): docs/ZIRH2-PINMAP.md and
info-zirh2.yaml. Remaining before a ZIRH-2 tapeout, all administrative:
create the repo FROM THE TEMPLATE when a shuttle is chosen, carry the
manifest over, and resolve the two flow-plumbing items listed in its
header (ROM_HEX into the TT flow, MACROS into src/config.json). The
hold margin at 79 ps stays the number to re-check on every run.

8x2 probe result (2026-08-07): the shrunk P0 top (N=64 rings, 64-byte
ECC RAM, 3213 FFs) hardens CLEAN on a double-width TT strip
(1708.8 x 313.74 um): utilization 66.7% at placement / 74.9% final,
setup +6.48 ns (fmax ~74 MHz, nominal 20), hold +0.11 ns, TNS 0/0,
DRC/LVS/antenna 0, all 3213 flops in the final netlist. The
pre-shrink top (4289 FFs) had failed at a forced 86% density -
recorded as the measured boundary of the tile. CAN VERDICT: at ~75%
final utilization there is no honest room for a CAN controller plus
the chain-A macro premium; CAN stays out of ZIRH-2 unless a later
optimization frees ~15% of the die. Next: N=64 macro hardening +
MACROS binding for chain A, pin map freeze, TT manifest.

P0 status (2026-08-07): COMPLETE. All blocks below exist, are tested and
synthesis-checked on the zirh2-p0 branch; tt_um_hma_zirh2 measures 4289
FFs with the real firmware and its integration test captures a v2
telemetry frame carrying a live, changing CPU signature. Remaining before
a ZIRH-2 tapeout: the hardening probe (area/timing on an 8x2-class die),
macro rebuild at N=128 + MACROS binding for chain A, pin map freeze and
the TT manifest.

P0 - the chip does not tape out without these:

| Block | Notes |
|---|---|
| zirh_bus | Single-master, read/write strobe + ready; no burst, no arbitration. Smallest thing SERV can talk through |
| SERV core (TMR state) | Bit-serial RV32I. Small enough that full TMR on its state is affordable; vendor copy in src/, pinned commit |
| Mask ROM + fw/ | Synthesized-constant ROM. Firmware: housekeeping loop that reads the monitor, computes a liveness signature, writes telemetry fields. riscv-none-elf-gcc + ROM generator script |
| ECC RAM | Hamming SECDED (32+7). Size set by measurement, likely 64-128 bytes. Correctable/uncorrectable counters exported to telemetry |
| zirh_seu_mon v2 | The placement A/B pair above; N per chain sized to remaining area |
| zirh_rs422 + command path | RX becomes a real command port (baud divisor register, counter clear, mode select via bus); TX keeps telemetry priority |
| zirh_tlm v2 | Versioned frame (spare STATUS encoding or a length byte). New fields: CPU liveness signature, ECC corrected/uncorrected, per-chain ESCAPE. Ground station extends, stays backward compatible with ZIRH-1 frames |

P1 - included if area and schedule allow, in this order:

| Block | Notes |
|---|---|
| SRAM DUT | Foundry SRAM macro + pattern-scan FSM, MBU address logging. GATED on an open question: sg13g2 SRAM macro availability in the TT flow - investigate before designing anything |
| zirh_can | CAN 2.0A, TMR on protocol FSM. Needs 2 pins |

P2 - explicitly out unless P0+P1 land early and small:

- SpaceWire-lite, NPU. Both were ZIRH-1 promises once; they are the first
  cut for the same reason they were cut then.

## Flow work (not RTL, but on the critical path)

1. **Placement constraints for TMR replicas.** Prototype phase 1 is DONE
   (2026-08-07), measured on ZIRH-1's final DEF with
   scripts/replica_dist.py:

   - All 387 same-bit replica trios in the design analyzed. Worst same-bit
     separation 3.78 um, median ~7.3 um, maximum 12.2 um.
   - 0% of same-bit pairs closer than 2 um; 25% closer than 5 um; 95%
     closer than 10 um.
   - Interpretation: the placer CLUSTERS same-bit trios rather than
     scattering them - all three replicas feed one voter gate, and
     wirelength optimization pulls them toward it. The clustering is
     structural, so it will not improve on its own in ZIRH-2's denser
     floorplan; if anything it worsens. No pair sits in the classic
     charge-sharing range (<2 um), but a quarter sit in the 3.8-5 um band
     that high-LET events can reach. ZIRH-1's ESCAPE counter puts physics
     numbers on exactly this layout.
   - Rejected idea, for the record: rotating bit order per replica in RTL
     does not help, because the voter gate remains the shared attractor
     for each trio regardless of bit naming.

   Mechanism survey for enforcing separation (phase 2, to be tested):

   - **Macro route - the only one available inside the TT flow today,
     and PROVEN in phase 3 (2026-08-07).** The macro.yaml workflow hardens
     zirh_tmr_ff256 standalone with the same tool stack the TT action uses
     (librelane 3.0.5, dockerized, same PDK hash) and delivers LEF + GDS.
     Measured on the hardened macro: die 50.7k um2, 52% utilization,
     setup +14.1 ns / hold +3.5 ns, DRC/LVS/antenna 0, and exactly 256
     flops in the final netlist.

     The honest cost number: one replica as a macro occupies ~50.7k um2 of
     die against ~12.5k um2 of flop area flat - the 514 signal pins make
     the block pin-limited, roughly a 4x area premium for separability.
     Three constrained replicas (chain A of the A/B experiment) would take
     ~152k um2, half of an 8x2 tile's usable area at N=256. Consequence:
     the constrained chain must be shorter than 256 bits (N=64..128, area
     scales roughly with pin count) OR the premium is accepted and the
     rest of the chip shrinks. This is now a sizing decision with real
     numbers behind it, gated on nothing.
   - DEF GROUPS/REGIONS fences: OpenROAD's placers honor them, but
     LibreLane exposes no configuration variable to define them and the
     TT action does not accept custom flow steps. Available only with a
     forked flow; keep as fallback.
   - FP_DEF_TEMPLATE: copies pin locations and die area only, not
     regions. Not applicable.

   **Phase 4 result (2026-08-07): the mechanism is PROVEN end to end.**
   macro/p4_sep_test.v pins three replica macros to (60,60), (392,320)
   and (724,60) through the MACROS object; the p4 workflow hardened it
   and verified the final DEF: all three FIXED within 0.00 um of the
   request, pairwise separations 422/422/664 um against the tool-placed
   baseline of 3.8-12 um. DRC (route and Magic) 0, LVS 0. Costs
   measured: setup slack drops from +11.4 ns (flat ZIRH-1) to +7.7 ns -
   crossing hundreds of um costs ~3.7 ns, still enormous margin at
   20 MHz - and the CI runtime rises to ~55 min, dominated by routing
   1536 macro pins over long spans. The A/B experiment is now
   designable; remaining open item from the phase audit: cross-macro
   clock skew was not present in the metrics set and must be pulled
   from the STA reports during ZIRH-2 integration.
2. check_tmr.sh extended per block, as in ZIRH-1 (positive + negative).
3. FPGA twin from day one - SERV firmware development against the twin,
   not against simulation only.
4. GL gating in CI unchanged.

## Decision gates

| Gate | Blocks waiting on it |
|---|---|
| ZIRH-1 silicon ESCAPE data | Final priority of placement A/B; chain sizing |
| SRAM macro availability in TT/IHP flow | SRAM DUT exists or not |
| Placement-constraint prototype on ZIRH-1 netlist | The A/B experiment; possibly the whole ZIRH-2 shape |
| Shuttle calendar (next IHP shuttle) | Everything; scope cuts follow the date |

## Risks, named

- **Area estimates.** ZIRH-1's utilization estimate was off by 5x until
  synthesis said otherwise. Every P0 block gets synthesized standalone and
  measured before integration; the budget table lives in this file and is
  updated with measured numbers only.
- **ROM size.** Synthesized-constant ROM area grows linearly with firmware
  size; the housekeeping loop must fit in ~1 KB or the ROM eats the RAM
  budget. Firmware size is a hardware constraint here.
- **SERV integration depth.** SERV is external IP; TMR-wrapping its state
  without forking it needs care (register file is the bulk - SERV's RF is
  SRAM/shift-register based, decide protection story explicitly).
- **Placement flow.** Named above; prototype first.

## What ZIRH-1 hands over

Verified TMR library, UART, telemetry framer and monitor architecture;
check_tmr methodology with its negative test; the CI shape (test + GL +
precheck gating); the FPGA twin flow; the ground station. ZIRH-2 is these
plus a computer, minus nothing.

## ZIRH-3 experiment candidates (recorded 2026-08-07)

Two techniques proposed for the platform, assessed against ZIRH-2's
measured constraints (81% utilization, no on-die clock generation) and
recorded here in the form this project accepts ideas: as experiments
with a number to produce.

### 1. Region-gated clock hold-and-heal - as an A/B experiment

The literature technique: partition the clock tree into independent
regions; on SET detection, gate only that region's clock for a few
cycles while state is corrected.

Assessment against this architecture, honestly: ZIRH's TMR heals
THROUGH clocking - the voted feedback overwrites a corrupted replica on
the next edge (verified per-block, single-cycle, in every unit suite).
Gating a region's clock on error would suspend exactly that healing and
widen the window in which a second strike becomes an uncorrectable
double error. It also contradicts a recorded ZIRH-1 design decision
(zirh_clk_rst: single clock domain, because every gated root is a new
SET-sensitive point that can silence a whole region in one hit), and it
does not fit ZIRH-2's die.

What survives of the idea is its containment core, and the honest way
to evaluate it is the same way this platform evaluated placement
separation: two matched storage regions, one behind a clock gate with
hold-on-error, one free-running with plain voted-feedback TMR, same
die, same beam. Deliverables: upset and escape rates per region, plus
the gate root's own SET contribution. If gating earns its area, the
number will say so; the prediction recorded here is that voted-feedback
healing wins on this PDK, and the experiment exists to check the
prediction, not to assume it.

### 2. Self-healing PLL - adapted to what the die actually has

The literature technique: DPLL control state protected by ECC, giving
millisecond-class automatic recovery from SEFI.

Assessment: ZIRH chips have no PLL - the clock arrives from the TT
harness and no on-die generation exists to protect. The PRINCIPLE the
technique embodies (protected control state, automatic SEFI exit) is
already this platform's spine, with silicon-bound instances: the TMR'd
BAUD divisor (a corrupted divisor kills the link; verified to heal with
the link alive), the TMR'd housekeeping mode/warm-up state, and the bus
watchdog's sub-millisecond exit from a wedged peripheral.

What is genuinely missing and small enough to matter: a CLOCK-LOSS
OBSERVER - a free-running ring-oscillator-clocked watchdog that detects
the external clock stuck (the one SEFI the synchronous die cannot see
about itself) and raises a pin plus a latched flag readable after
recovery. Ring oscillator in standard cells, a handful of gates.
Deliverable: external-clock SEFI visibility from the ground, and the
observer's own upset rate as a bonus measurement.

Both candidates wait for ZIRH-2 beam data before any RTL: the A/B
methodology they would use is the one ZIRH-2 is about to validate in
silicon.

## PDN/macro integration record (2026-08-07, first all-green CI)

The bound-macro chip's road through TT precheck took three measured
diagnosis layers, recorded here because every one generalizes to any
IHP macro integration:

1. Symptom: precheck rejected power ports >10 um from the die edge.
   Geometry (final DEF): the vertical TopMetal1 stripes split at every
   macro column - the macro's own hardening had used the full metal
   stack, and its TopMetal1/2 geometry blocked the chip stripes.
   Fix: re-harden the macro capped at Metal5 (internal PDN on
   Metal4/Metal5, core ring), same 113.75 x 132.47 um footprint. The
   macro workflow now gates on ZERO TopMetal entries in the LEF.
2. New failure: PDN-0232/0233 - the chip grid generated no shapes for
   the macro instances. Root cause read from LibreLane 3.0.5 source:
   the default macro grid carries exactly one connect rule,
   PDN_VERTICAL_LAYER<->PDN_HORIZONTAL_LAYER (TopMetal1<->TopMetal2),
   which can never touch a macro whose pins sit below the TopMetals.
   On sky130 this works by accident (top straps share met5 with macro
   pins); on IHP's two-TopMetal stack it structurally cannot.
   Fix: src/pdn.tcl - the byte-for-byte LibreLane default plus two
   marked connect rules (Metal5<->TopMetal1, Metal4<->Metal5),
   selected via PDN_CFG.
3. Independently: the GL simulation needs the macro's own gate netlist
   linked (blackboxes in the top netlist), from macro/hardened64/.

With all three in: gds, precheck, gl_test and viewer green in one run,
with chain A bound at 700/680/1380 um separation and chain B
tool-placed on the same die. The A/B experiment is submission-ready.

## v2.1 upgrade record (2026-08-08)

Approved as one package: UART command set + boot-time ROM checksum
(mask contents - closed the injection loop the pin map left open), the
CPU watchdog with SoC-only reset and a telemetry BOOT counter,
bus-timeout and frame-error counters, frame v2.1 ('5A 33', 20 bytes),
the tlm2 unit suite, a top-level RF fault campaign, and an FPGA
feasibility measurement (~3540 LUT with BRAM absorption of RF and ECC
RAM: fits an iCE40UP5K by estimate; functional twin still needs a real
bitstream because the ECC RAM's combinational read may not survive
BRAM mapping).

Measured finding worth the whole exercise - the ZOMBIE class: an RF
flip can corrupt a hoisted base pointer so one peripheral path dies
while the loop and its rolling signature stay alive, keeping the
watchdog fed. Signature liveness is NOT command-path liveness. Two
answers shipped: the firmware performs a voluntary warm restart every
2^22 iterations (minutes at silicon rate, unreachable in simulation),
re-deriving all register state from ROM constants; and the fault
campaign's contract distinguishes SURVIVED / REBOOTED / ZOMBIE with
one hard assertion - a frozen signature with no reboot never happens.
Top grows to 3382 FFs; the SoC synthesis check is now explicitly
firmware-dependent (real ROM constants steer SERV's optimization).

## v2.2 environment instruments (2026-08-08)

Literature sweep looking for measurement value the tile was not yet
capturing settled on three additions, chosen because every one is
pin-free, digital-only, and small enough for the ~78% post-v2.1
utilization; all read over the existing UART command path (hk registers
0x38/0x3C, commands 'T'/'S'/'B'/'E'), and the telemetry frame stays at
v2.1 - the frame is the autonomous heartbeat, these are polled
instruments.

TID SENSOR ('T'): an enable-gated 64-stage ring oscillator counted by an
asynchronous ripple counter over a fixed 1024-cycle window. Total
ionizing dose shifts thresholds and the frequency drifts with
accumulated dose; ring-oscillator dosimetry is demonstrated across
nodes from 250 nm bulk to 22 nm FD-SOI (e.g. the IEEE TNS 22-nm FD-SOI
and 28-nm FD-SOI ring-oscillator TID studies). SEU counters measure the
beam's discrete hits; this measures the accumulating damage - a second
physical observable for the cost of ~130 flops and two NAND-worth of
analog nothing.

SET CATCHER ('S', self-test 'E'): a quiet 64-stage inverter chain
watched by a cross-coupled NAND catch latch - the self-triggered capture
structure of Narasimham et al. (IEEE TNS 2006, on-chip SET pulse-width
characterization, 130/90 nm), also built on IHP 250 nm bulk (Design of
an On-chip System for the SET Pulse Width Measurement, 2017). This
version records occurrence, not width - a width digitizer needs a
Vernier chain the tile has no room for, and is recorded as a ZIRH-3
candidate. Combinational transients are invisible to every other
counter on the die; the chain is the third particle detector after the
flop rings and the ECC RAM, and 'E' proves it alive from the ground.

BURST CORRELATOR ('B'): counts ring-event onsets arriving within 16
cycles of a previous onset. MCU/MBU characterization work (heavy-ion
DFF-chain statistics in 180 nm, satellite SRAM observations) treats
spatial and temporal clustering as the signature separating multi-cell
strikes from Poisson background; the correlator preserves that
statistic on-chip where saturating counters would erase it after the
fact.

Mechanics worth recording: the oscillator and chain are hand-instantiated
SG13G2 cells with (* keep *) inside keep_hierarchy islands (synthesis
folds an inverter chain to a wire otherwise); RTL simulation swaps them
for behavioral models under ZIRH_SIM_ENV because a zero-delay
combinational loop hangs event-driven simulation, and gate-level runs
keep the real cells but must never enable the oscillator - the 'T'
exercise is RTL-and-silicon only. A dead env block leaves 'T' busy-wait
stuck by design: the CPU watchdog converts that into a counted reboot.
