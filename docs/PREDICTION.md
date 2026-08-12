# Pre-beam prediction: ESCAPE(A) vs ESCAPE(B)

Registered before any beam exposure. The git history of this file is
the timestamp; the numbers below were produced by the systematic
gate-level SEU sweep (test/test_gl_seu_sweep.py) and the layout
analysis (scripts/seu_predict.py) on the shipped netlist and DEF.
Nothing here may be edited after beam data exists - a post-beam
comparison goes in a separate document.

## The two chains

Chain A and chain B are logically IDENTICAL 32-bit TMR shift rings
with voted feedback, fed by the same pattern source, counted by the
same counter design. They differ in exactly one thing: chain A's three
replicas are bound to three hard macros placed 680-1380 um apart;
chain B's replicas were left to the placer. Any difference the beam
measures between ESC(A) and ESC(B) is therefore a measurement of
placement, not logic.

## What simulation establishes (gate level, netlist that ships)

The sweep injects on the as-placed netlist at silicon timings:

1. **Singles - exhaustive.** All 192 replica flops (2 chains x 3
   replicas x 32 bits), each flipped in both pattern phases: 384
   injections. Result contract: every injection lands as exactly one
   RAW count; ZERO escapes in either chain. The voted feedback heals a
   lone upset in one cycle.

2. **Pairs - the escape window.** Cross-replica double flips, all 32
   bits of both chains, three geometries:
   - same bit, same cycle: escapes, exactly once per pair (voter
     majority broken at that bit);
   - same bit, one cycle apart: zero escapes (the first flip healed
     before the second landed);
   - different bits, same cycle: zero escapes (each bit keeps its
     2-of-3 majority).

So an escape REQUIRES the same bit upset in two replicas within one
clock cycle. The chains are identical in this response - simulated
escape behaviour gives no reason for ESC(A) and ESC(B) to differ. The
beam escape ratio is therefore a pure measurement of the probability
that one particle (or one particle's charge-sharing footprint) upsets
two same-bit replicas simultaneously - a spatial quantity.

## What the layout says (final DEF of the shipped GDS)

Same-bit cross-replica flop distances, measured:

| quantity | chain A (macro-bound) | chain B (tool-placed) |
|---|---|---|
| closest same-bit pair | >= 680 um (macro separation floor) | 3.78 um |
| median same-bit pair | ~700 um | 7.62 um |
| pairs under 5 um | 0 | 35 of 96 |

Folding a charge-sharing range model P(double) ~ exp(-d/lambda) over
these distances (lambda = the collection range; 130 nm bulk dual-node
studies put meaningful charge sharing below ~2 um, negligible beyond a
few um - Amusan et al. TNS 2006, Narasimham et al.):

| lambda (um) | S_B = sum exp(-d/lambda) | S_A | ratio B/A |
|---|---|---|---|
| 0.25 | 6.0e-06 | 0 (< 1e-300) | effectively infinite |
| 0.5 | 1.4e-02 | 0 | effectively infinite |
| 1.0 | 0.71 | < 1e-295 | effectively infinite |
| 2.0 | 5.8 | < 1e-147 | effectively infinite |
| 4.0 | 20 | < 1e-73 | effectively infinite |

## The registered prediction

1. **ESC(B) > 0 at sufficient LET.** Chain B has 35 same-bit pairs
   inside 5 um; at high LET and especially at tilted incidence
   (charge-sharing footprints elongate along the track), same-bit
   simultaneous double upsets will occur and each one is exactly one
   ESC_B count. ESC_B rate should grow super-linearly with LET and
   with tilt angle, tracking the closest-pair distance spectrum above.

2. **ESC(A) consistent with zero from charge sharing.** No single
   particle can span 680 um. Chain A escapes only by the accidental
   coincidence of two INDEPENDENT particles hitting the same bit's two
   replicas within one 50 ns cycle. At a typical test flux, with
   per-bit upset rate r (measurable live as RAW_A/32 per second), the
   accidental rate is about 3 x 32 x r^2 x 50 ns - for r = 1 upset/bit/s
   (already a hot beam) that is ~5e-6 escapes per second, orders below
   any measurable ESC_B. Prediction: ESC(A) = 0 within counting
   statistics for any practical fluence.

3. **RAW(A) equals RAW(B) within statistics.** Both chains present the
   same 96 flops to the beam; detection is not placement-sensitive.
   This is the built-in control: if RAW rates differ significantly,
   the chains saw different effective cross sections and the escape
   comparison must be renormalized by RAW before interpretation.

4. **Falsification criteria.** A statistically significant ESC_A
   excess over the accidental-coincidence rate falsifies claim 2 and
   indicates an escape mechanism outside the same-bit-same-cycle
   window - a voter SET, a clock-tree SET, or an angle effect the
   model missed; the singles/pairs sweep data above is the reference
   for separating those. ESC_B remaining at zero at high LET and high
   tilt would falsify claim 1 and bound lambda below the 3.78 um
   closest pair.

## Method note

Injection mechanics: Force/Release on the replica output nets
(u_hk.{a,b}_q{a,b,c}[bit]) across exactly one capture edge, on the
gate-level netlist with silicon timing models - the discipline the
RTL flip suites and the GL fault campaign converged on. Counters are
read over the same UART telemetry the beamline will use, so the sweep
also re-proves the observation path end to end.
