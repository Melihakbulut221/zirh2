# Placement Governs TMR Escape: A Pre-Registered Prediction from a Low-Cost Radiation-Effects Observatory ASIC

Draft manuscript. Target venue: RADECS / NSREC data workshop track.
The pre-beam prediction this paper registers is frozen in
docs/PREDICTION.md; the git history of that file is the registration
timestamp. Beam results, when they exist, go into Section VII of a
revised version - nothing in Sections I-VI may change after exposure.

## Abstract

Triple modular redundancy fails when one particle upsets two replicas
of the same bit at once, so the escape rate of a TMR structure should
be governed by the physical distance between its replicas rather than
by its logic. We test this directly on ZIRH-2, a self-instrumented
radiation-effects observatory fabricated on the open IHP SG13G2 130 nm
BiCMOS process through the TinyTapeout multi-project service. The chip
carries two logically identical 32-bit TMR shift chains with voted
feedback that differ in exactly one respect: chain A binds its three
replicas to hard macros placed 680-1380 um apart, while chain B leaves
placement to the tool, which produced same-bit replica spacings down
to 3.8 um. An exhaustive gate-level fault-injection campaign on the
shipped netlist (384 single-flop upsets, 192 cross-replica pairs in
three geometries) establishes that the only escaping fault geometry is
two replicas of the same bit upset within the same clock cycle, and
that the chains are indistinguishable in their logical response. The
measured escape ratio under beam is therefore a pure measurement of
spatial simultaneous-double-upset probability. We register the
quantitative prediction before irradiation: ESC(B) measurable and
rising super-linearly with LET and tilt; ESC(A) consistent with zero,
bounded by an accidental-coincidence rate of order 3Nr^2t_clk; RAW(A)
equal to RAW(B) within statistics as the built-in cross-section
control. The methodology - publish the prediction, then irradiate -
costs nothing extra and converts a counting experiment into a test of
a falsifiable model.

## I. Introduction

Charge sharing between adjacent nodes is the dominant defeat mechanism
for spatial redundancy in deep-submicron bulk processes: a single ion
track can deposit charge in two nodes tens of micrometres apart at
grazing incidence, and dual-node upset studies at 130 nm place
meaningful charge collection within a few micrometres of the strike
[1], [2]. The standard mitigation is physical separation of TMR
replicas or of the redundant nodes of hardened cells [3]. The
separation distances actually chosen in practice, however, are usually
justified by simulation of the process, not by an experiment on the
shipped layout: measured escape-versus-spacing data on real fabricated
logic remains scarce, particularly on open-source processes where the
full layout is publishable.

This paper describes an experiment designed to produce exactly that
measurement, with the prediction registered publicly before beam time.
Two TMR shift chains, identical to the gate, differ only in replica
placement. Every quantity needed to predict their relative escape
rates - the escape window of the logic and the distance spectrum of
the layout - is extracted beforehand: the first by exhaustive
gate-level fault injection on the final netlist, the second from the
final DEF. If the beam measurement matches the prediction, the
placement floor bought by the macro binding is quantified; if it does
not, the discrepancy localizes a mechanism outside the model (voter
SET, clock SET, angular effects), which the injection data helps
separate. Either outcome is informative, which is the point of
registering the prediction first.

The vehicle is deliberately low-cost: a 160 x 100 um^2 hard-macro pair
on a TinyTapeout SG13G2 multi-project die, a bit-serial RISC-V
computer, and a UART. The entire observatory - detectors, computer,
telemetry, and the fault-injection rehearsal of the beam campaign -
fits the budget of a student project, and every artifact from RTL to
GDS is public.

## II. The vehicle: ZIRH-2

ZIRH-2 is a radiation-effects observatory: its purpose is to measure
upsets in itself and report them over channels that survive the
upsets. The die hosts:

- **Three monitor rings** fed by a shared pattern source: a PLAIN
  32-bit shift ring (no protection, the per-flop upset-rate
  reference); TMR ring A, three 32-bit replicas bound to three hard
  macros with voted feedback; TMR ring B, identical logic,
  tool-placed. Each TMR ring exports two counters: RAW increments on
  any replica-vs-replica mismatch (a detected upset, healed by the
  voted feedback in one cycle) and ESC increments when the voted
  output itself is wrong (an escape - the event TMR exists to
  prevent).
- **A bit-serial RISC-V computer** (SERV [4]) running from a
  synthesized-constant mask ROM, with an ECC-protected register file
  and a watchdog that reboots only the computer: the instruments and
  the telemetry path never see the reset, so escapes and reboots are
  counted across computer failures.
- **Two telemetry voices**: the primary UART (firmware-driven,
  command-capable) and a CPU-untouchable hardware mirror of the same
  frame stream, so ground truth survives both computer death and
  command-channel flooding.
- **Environment instruments** (a ring-oscillator TID sensor, an
  SET-catcher chain, a burst correlator) that widen the observatory
  beyond SEU counting; they are described elsewhere and not used in
  this experiment.

All counters are themselves TMR with voted feedback; infrastructure
mismatches are exported on a separate error pin so instrument health
is observable independently of the quantities under test.

The two chains under study differ in one line of the floorplan. Chain
A's three replicas are the three instances of a hardened 32-flop
macro, fixed at x = 100, 800 and 1480 um on a 7.5 um row - pairwise
separations of 680, 700 and 1380 um. Chain B's 96 flops went through
the standard placer with no constraint. Both chains close timing on
the same clock and pass the same gate-level verification.

## III. Method: the escape window, measured exhaustively

Fault injection runs on the shipped netlist - post-place-and-route,
silicon timing models, the exact GDS geometry - driven through the
same UART telemetry the beamline will use, so every campaign run also
re-proves the observation path. Injection follows the
force-one-capture-edge discipline: the replica output net is forced
inverted across exactly one clock edge and released, the gate-level
equivalent of a state flip lasting one cycle.

**Singles, exhaustive.** Every replica flop of both chains - 2 chains
x 3 replicas x 32 bits - flipped one at a time in both phases of the
test pattern: 384 injections. Contract: each lands as exactly one RAW
count in its own chain; ESC stays exactly zero everywhere. This is the
one-cycle-heal property of voted feedback proven flop by flop on the
placed netlist rather than asserted from the RTL.

**Pairs, the escape geometry.** Cross-replica double flips on all 32
bits of both chains in three geometries: same bit same cycle (the
majority at that bit is broken: must escape, exactly once per pair);
same bit one cycle apart (the first flip has healed: must not escape);
different bits same cycle (each bit keeps a 2-of-3 majority: must not
escape). 192 pairs total, with exact counter equalities asserted,
including the RAW arithmetic (one mismatch-cycle for simultaneous
pairs, two for staggered ones).

The result defines the escape window: an escape requires the same bit
upset in two replicas within one clock cycle, and the two chains are
logically indistinguishable in this response. Everything that can
differ under beam is therefore spatial.

**Formal closure of the window.** The injection campaign samples; a
formal harness proves. The shipped replica primitive and the shipped
voted-feedback structure, wrapped with free upset inputs, are checked
by unbounded k-induction (yosys-smtbmc with z3) at ring widths 4, 8
and the shipping 32: under an arbitrary infinite upset stream
confined to one replica per cycle - any bits, every cycle - the voted
output equals a golden reference in every bit of every cycle. The
dual cover property lets the solver construct the escape itself
(Fig. 1): a same-bit two-replica hit breaks the majority, the corrupted
vote enters the feedback, and the wrong bit walks the ring to the
output. The escape window claim is thus machine-checked in both
directions rather than inferred from samples.

**Layout metric.** From the final DEF, the distance between same-bit
replica flops: chain B has 96 same-bit pairs with minimum 3.78 um,
median 7.62 um, and 35 pairs closer than 5 um; chain A's floor is the
macro separation, at least 680 um. Folding a charge-sharing range
model P(double) ~ exp(-d/lambda) over both spectra, the predicted
single-particle escape ratio B/A exceeds 10^100 for any lambda between
0.25 and 4 um - that is, chain A single-particle escapes are not rare
but excluded, for any physically plausible collection range at this
node [1].

![Fig. 1 - the escape, drawn by the solver: a same-bit double hit
(flip_a = flip_b = 0x08) corrupts two replicas, the broken majority
enters the voted feedback (all three replicas agree wrong one cycle
later), and the error walks the ring to the output while the golden
ring stays clean.](fig/escape_witness.png)

## IV. Simulation results

The sweep runs inside the project's continuous integration on every
hardening run, so the numbers below are re-proven against the exact
netlist that ships:

| campaign | injections | RAW counted | ESC counted | contract |
|---|---|---|---|---|
| singles, chain A | 192 | 192 | 0 | met |
| singles, chain B | 192 | 192 | 0 | met |
| same-bit same-cycle pairs | 32 + 32 | 32 + 32 | 32 + 32 | met (every pair escapes once) |
| same-bit staggered pairs | 32 + 32 | 64 + 64 | 0 | met |
| different-bit same-cycle pairs | 32 + 32 | 32 + 32 | 0 | met |

After each campaign the computer answers an echo probe: no injection
sequence wedges the chip.

## V. The registered prediction

1. **ESC(B) > 0 at sufficient LET**, rising super-linearly with LET
   and with tilt angle as the charge-sharing footprint elongates
   across chain B's 3.8-30 um same-bit pair spectrum. Each event is
   exactly one ESC_B count.
2. **ESC(A) consistent with zero.** No single particle spans 680 um.
   The only chain-A escape mechanism inside the window is two
   independent particles striking the same bit's two replicas within
   one 50 ns cycle: rate ~ 3 x 32 x r^2 x 50 ns for per-bit upset rate
   r. At r = 1 upset/bit/s - already a hot beam - that is 5 x 10^-6
   escapes per second, unobservable at practical fluences.
3. **RAW(A) = RAW(B) within counting statistics.** Both chains present
   96 identical flops; detection is placement-blind. This is the
   built-in control: a significant RAW asymmetry means the chains saw
   different effective cross sections and the escape comparison must
   be renormalized before interpretation.
4. **Falsification.** A significant ESC_A excess over the coincidence
   bound falsifies the model and localizes a mechanism outside the
   escape window - voter SET, clock SET, or an angular effect - which
   the exhaustive singles data provides the reference to separate.
   ESC_B remaining zero at high LET and tilt bounds lambda below the
   3.78 um closest pair, itself a publishable constraint at this node.

## VI. Beam plan

Heavy-ion or proton exposure with live telemetry: RAW_A, RAW_B, ESC_A,
ESC_B, and the PLAIN reference streamed each frame; boot counter
separating computer reboots from instrument events; the mirror channel
recording ground truth through any command-path saturation. An LET
scan at normal incidence, then a tilt scan at fixed LET along and
across chain B's placement rows (the pair-distance spectrum is
anisotropic; the DEF predicts which tilt azimuth maximizes ESC_B). The
fault-injection campaign doubles as the bench rehearsal: the same
scripts, the same serial contract, the same counters.

## VII. Post-beam comparison

Reserved. This section is empty by design until beam data exists.

## References

[1] O. A. Amusan et al., "Charge collection and charge sharing in a
130 nm CMOS technology," IEEE Trans. Nucl. Sci., vol. 53, no. 6, 2006.

[2] B. Narasimham et al., "Characterization of digital single event
transient pulse-widths in 130-nm and 90-nm CMOS technologies," IEEE
Trans. Nucl. Sci., vol. 54, no. 6, 2007.

[3] L. R. Rockett, "Designing hardened bulk/SOI CMOS circuits for
space radiation environments," and related dual-node separation
literature.

[4] O. Kindgren, "SERV: the SErial RISC-V CPU," open-source hardware,
https://github.com/olofk/serv.

[5] M. Venn, "Tiny Tapeout: democratizing ASIC design,"
https://tinytapeout.com; IHP SG13G2 open-source PDK,
https://github.com/IHP-GmbH/IHP-Open-PDK.
